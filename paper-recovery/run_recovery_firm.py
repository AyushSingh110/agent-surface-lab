"""Step 1 firm-up: re-run only the ARGUMENT-CRITICAL recovery cells at N=10.

The action-licensing claim rests on a contrast (declarative_neutral BAD vs
lookup_permitting/reflect GOOD, with imperative in between). This raises N to 10 on
exactly those skipped-lookup arms across all depths, plus all arms on the date+hhmm
surface-form cells (the "unrecoverable" headline). Version (n=6) is left as the
flagged noisy outlier and NOT run here.

Usage: python paper-recovery/run_recovery_firm.py --run data/v2batch --n 10
Requires labels.json + a live Ollama server.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from harness.backend import OllamaBackend
from harness.config import load_config
from harness.interventions import no_op, reflect_and_retry, restart_clean, rollback_n
from harness.metrics import ReplayOutcome, iatrogenic_rate, mean_recovery, net_improvement
from harness.replay import InterventionOutcome, reconstruct, replay_cell
from harness.tools import ToolRegistry
from harness.trace import TraceRecord
from recovery_sandbox.v2_tasks import REQUIREMENT_CORES, V2_TASKS
from recovery_sandbox.v2_tools import build_v2_tools

TASKS = {t.id: t for t in V2_TASKS}
DEPTH = {t.id: t.trigger_depth for t in V2_TASKS}
SF_FORM = {"SM-01": "date", "SM-02": "date", "SM-03": "date", "SM-04": "date", "SM-05": "date",
           "SF-01": "hhmm", "SF-02": "hhmm", "SF-04": "version"}
CONTROL = "no_op"

PHRASINGS = {
    "req_imperative_only": "Report only {core}.",
    "req_imperative_plain": "Report {core}.",
    "req_declarative_neutral": "The answer must be {core}.",
    "req_declarative_lookup_permitting": "Report {core}; use tools to verify.",
}
# argument-critical arms for skipped-lookup (the contrast); rollback/restart excluded.
SL_ARMS = ["no_op", "reflect_and_retry", "req_imperative_only", "req_imperative_plain",
           "req_declarative_neutral", "req_declarative_lookup_permitting"]
# surface-form headline uses the full arm set.
SF_ARMS = ["no_op", "reflect_and_retry", "rollback_2", "restart_clean"] + list(PHRASINGS)
SF_FORMS_RUN = {"date", "hhmm"}  # version left as flagged outlier


def _phrasing_arm(name: str, template: str, core: str):
    sentence = template.format(core=core)

    def _f(trace: TraceRecord, k: int, config) -> InterventionOutcome:
        msgs = reconstruct(trace, k)
        msgs.append({"role": "user", "content": f"You must satisfy this requirement: {sentence}"})
        return InterventionOutcome(msgs, k, name, sentence)

    return _f


def _arm(name: str, task_id: str):
    return {"no_op": no_op, "reflect_and_retry": reflect_and_retry,
            "rollback_2": rollback_n(2), "restart_clean": restart_clean}.get(name) \
        or _phrasing_arm(name, PHRASINGS[name], REQUIREMENT_CORES[task_id])


def _load(run_dir: Path):
    labels = json.loads((run_dir / "labels.json").read_text(encoding="utf-8-sig"))
    traces = {t.trace_id: t for t in (TraceRecord.from_json_line(l)
              for l in (run_dir / "traces.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}
    out = []
    for tid, lab in labels.items():
        if lab["failure_class"] not in ("skipped_lookup", "surface_form_misuse"):
            continue
        tr = traces[tid]
        tr.failure_class = lab["failure_class"]
        tr.failure_step_k = int(lab["failure_step_k"])
        out.append(tr)
    return out


def run(run_dir: Path, n: int, config_yaml: Path | None) -> None:
    config = load_config(config_yaml)
    backend = OllamaBackend(config.model_tag, config.ollama_host)
    traces = _load(run_dir)
    sl = [t for t in traces if t.failure_class == "skipped_lookup"]
    sf = [t for t in traces if t.failure_class == "surface_form_misuse"
          and SF_FORM.get(t.trace_id.split("-r")[0]) in SF_FORMS_RUN]
    plan = [(t, SL_ARMS) for t in sl] + [(t, SF_ARMS) for t in sf]
    total = sum(len(a) for _, a in plan)
    print(f"FIRM-UP N={n}: SL={len(sl)} x {len(SL_ARMS)} arms + SF(date+hhmm)={len(sf)} x {len(SF_ARMS)} arms")
    print(f"cells={total}  ~replays={total*n}  model={config.model_tag}")

    outdir = run_dir / "recovery_firm"
    outdir.mkdir(parents=True, exist_ok=True)
    cells_path = outdir / "cells.jsonl"

    # Resume: skip (trace_id, arm) cells already checkpointed (survives a crash).
    done_cells: set[tuple[str, str]] = set()
    if cells_path.is_file():
        for line in cells_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done_cells.add((r["trace_id"], r["intervention"]))
        print(f"resuming: {len(done_cells)} cells already done")

    done = len(done_cells)
    with cells_path.open("a", encoding="utf-8") as ckpt:
        for tr, arms in plan:
            task = TASKS[tr.trace_id.split("-r")[0]]
            for arm in arms:
                if (tr.trace_id, arm) in done_cells:
                    continue
                sb = outdir / tr.trace_id / arm
                reg = ToolRegistry([build_v2_tools(sb)[t] for t in task.tool_names])
                succ = replay_cell(trace=tr, k=tr.failure_step_k or 0, intervention=_arm(arm, task.id),
                                   tools=reg, backend=backend, config=config,
                                   verifier=task.make_verifier(sb), n=n)
                ckpt.write(json.dumps({"trace_id": tr.trace_id, "intervention": arm,
                                       "failure_class": tr.failure_class, "successes": sum(succ),
                                       "n": n, "dist": succ}) + "\n")
                ckpt.flush()  # checkpoint every cell so a disconnect can't wipe progress
                done += 1
                if done % 25 == 0:
                    print(f"  ...{done}/{total} cells")

    # Aggregate from the checkpoint (source of truth) -> outcomes + dists + results.json.
    outcomes: list[ReplayOutcome] = []
    dists: dict[str, dict[str, list[bool]]] = defaultdict(dict)
    for line in cells_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        outcomes.append(ReplayOutcome(trace_id=r["trace_id"], failure_class=r["failure_class"],
                                      intervention=r["intervention"], successes=r["successes"], n=r["n"]))
        dists[r["trace_id"]][r["intervention"]] = r["dist"]
    (outdir / "results.json").write_text(json.dumps(
        {"n": n, "outcomes": [vars(o) for o in outcomes], "distributions": dists}, indent=2), encoding="utf-8")
    _report(outcomes, dists, sl, sf, n)
    print(f"\nraw: {outdir/'results.json'}  ({len(outcomes)} cells)")


def _rate(cell):
    return sum(o.successes / o.n for o in cell) / len(cell) if cell else float("nan")


def _report(outcomes, dists, sl, sf, n) -> None:
    print("\n" + "=" * 74 + f"\nFIRM-UP RESULTS (N={n}) — DIRECTIONAL\n" + "=" * 74)
    print("\n=== skipped_lookup: recovery by arm x depth (rate; n traces) ===")
    print(f"{'arm':<36}" + "".join(f"d{d:<9}" for d in (1, 2, 3)))
    for arm in SL_ARMS:
        row = f"{arm:<36}"
        for d in (1, 2, 3):
            cell = [o for o in outcomes if o.failure_class == "skipped_lookup" and o.intervention == arm
                    and DEPTH[o.trace_id.split('-r')[0]] == d]
            row += (f"{_rate(cell):.2f}({len(cell)})".ljust(11)) if cell else "-".ljust(11)
        print(row)
    print("\n=== surface_form_misuse (date+hhmm): recovery by arm x form ===")
    print(f"{'arm':<36}" + "".join(f"{f:<11}" for f in ("date", "hhmm")))
    for arm in SF_ARMS:
        row = f"{arm:<36}"
        for f in ("date", "hhmm"):
            cell = [o for o in outcomes if o.failure_class == "surface_form_misuse" and o.intervention == arm
                    and SF_FORM.get(o.trace_id.split('-r')[0]) == f]
            row += (f"{_rate(cell):.2f}({len(cell)})".ljust(11)) if cell else "-".ljust(11)
        print(row)
    print("\n=== iatrogenic vs no_op (skipped_lookup, paired) ===")
    ctrl = [o for o in outcomes if o.failure_class == "skipped_lookup" and o.intervention == CONTROL]
    for arm in SL_ARMS:
        if arm == CONTROL:
            continue
        arm_o = [o for o in outcomes if o.failure_class == "skipped_lookup" and o.intervention == arm]
        pc = [o for o in ctrl if o.trace_id in {a.trace_id for a in arm_o}]
        if arm_o and len(pc) == len(arm_o):
            print(f"  {arm:<36}iatro={iatrogenic_rate(arm_o, pc):.2f}  net={net_improvement(arm_o, pc):+.2f}")


def main() -> None:
    p = argparse.ArgumentParser(description="Firm-up recovery sweep (argument-critical cells, N=10).")
    p.add_argument("--run", type=Path, default=Path("data/v2batch"))
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--config", type=Path, default=Path("paper-recovery/configs/kill_test.yaml"))
    args = p.parse_args()
    run(args.run, args.n, args.config)


if __name__ == "__main__":
    main()
