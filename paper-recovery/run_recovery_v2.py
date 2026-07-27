"""v2 recovery sweep: phrasing x arm x task-shape x depth on the labeled clean pools.

Runs the recovery machinery on the human-labeled v2 failing traces (skipped_lookup +
surface_form_misuse), crossing the intervention arms with 4 repair PHRASINGS on the
requirement arm. This is the real test of (i) whether the imperative/declarative
repair hypothesis generalizes beyond DR-4, and (ii) whether surface-form misuse is
recovery-resistant at real n.

Compute plan (protected regions run at full n):
  - skipped_lookup: no_op (full baseline) + 4 phrasing arms (FULL, protected) +
    reflect/rollback/restart on a depth-stratified subset (breadth).
  - surface_form_misuse: all 8 arms (FULL, protected).

Reports raw per-cell distributions, paired iatrogenic rate vs no_op, and
boundary-flagged cells. A NULL (arms indistinguishable) is reported plainly.

Usage: python paper-recovery/run_recovery_v2.py --run data/v2batch --n 3
Requires labels.json in the run dir (human-labeled) and a live Ollama server.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from harness.backend import OllamaBackend
from harness.config import load_config
from harness.interventions import no_op, reflect_and_retry, restart_clean, rollback_n
from harness.metrics import ReplayOutcome, is_near_boundary, iatrogenic_rate, mean_recovery, net_improvement
from harness.replay import InterventionOutcome, reconstruct, replay_cell
from harness.tools import ToolRegistry
from harness.trace import TraceRecord
from recovery_sandbox.v2_tasks import REQUIREMENT_CORES, V2_TASKS
from recovery_sandbox.v2_tools import build_v2_tools

TASKS = {t.id: t for t in V2_TASKS}
DEPTH = {t.id: t.trigger_depth for t in V2_TASKS}
CONTROL = "no_op"
SWEEP_CLASSES = {"skipped_lookup", "surface_form_misuse"}

PHRASINGS = {
    "req_imperative_only": "Report only {core}.",
    "req_imperative_plain": "Report {core}.",
    "req_declarative_neutral": "The answer must be {core}.",
    "req_declarative_lookup_permitting": "Report {core}; use tools to verify.",
}
BASE_ARMS = ["no_op", "reflect_and_retry", "rollback_2", "restart_clean"]
PROTECTED_SL = ["no_op"] + list(PHRASINGS)              # full on skipped_lookup
BREADTH_SL = ["reflect_and_retry", "rollback_2", "restart_clean"]  # subset on skipped_lookup


def _phrasing_arm(name: str, template: str, core: str):
    sentence = template.format(core=core)

    def _f(trace: TraceRecord, k: int, config) -> InterventionOutcome:
        msgs = reconstruct(trace, k)
        msgs.append({"role": "user", "content": f"You must satisfy this requirement: {sentence}"})
        return InterventionOutcome(msgs, k, name, sentence)

    return _f


def _arm(name: str, task_id: str):
    if name == "no_op":
        return no_op
    if name == "reflect_and_retry":
        return reflect_and_retry
    if name == "rollback_2":
        return rollback_n(2)
    if name == "restart_clean":
        return restart_clean
    return _phrasing_arm(name, PHRASINGS[name], REQUIREMENT_CORES[task_id])


def _load(run_dir: Path) -> list[TraceRecord]:
    labels = json.loads((run_dir / "labels.json").read_text(encoding="utf-8-sig"))
    traces = {t.trace_id: t for t in (TraceRecord.from_json_line(l)
              for l in (run_dir / "traces.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}
    out = []
    for tid, lab in labels.items():
        if lab["failure_class"] not in SWEEP_CLASSES:
            continue
        tr = traces[tid]
        tr.failure_class = lab["failure_class"]
        tr.failure_step_k = int(lab["failure_step_k"])
        out.append(tr)
    return out


def _breadth_subset(sl_traces: list[TraceRecord], cap: int = 8) -> set[str]:
    by_depth: dict[int, list[str]] = defaultdict(list)
    for tr in sl_traces:
        by_depth[DEPTH[tr.trace_id.split("-r")[0]]].append(tr.trace_id)
    keep: set[str] = set()
    for d, ids in by_depth.items():
        keep.update(sorted(ids)[:cap])
    return keep


def run(run_dir: Path, n: int, config_yaml: Path | None, limit: int | None = None) -> None:
    config = load_config(config_yaml)
    backend = OllamaBackend(config.model_tag, config.ollama_host)
    traces = _load(run_dir)
    if limit is not None:  # smoke test: first `limit` traces of each mechanism
        sl_ = [t for t in traces if t.failure_class == "skipped_lookup"][:limit]
        sf_ = [t for t in traces if t.failure_class == "surface_form_misuse"][:limit]
        traces = sl_ + sf_
    sl = [t for t in traces if t.failure_class == "skipped_lookup"]
    sf = [t for t in traces if t.failure_class == "surface_form_misuse"]
    breadth = _breadth_subset(sl)
    sweep_dir = run_dir / "recovery_v2"

    def arms_for(tr: TraceRecord) -> list[str]:
        if tr.failure_class == "surface_form_misuse":
            return BASE_ARMS + list(PHRASINGS)          # all 8, protected
        arms = list(PROTECTED_SL)                        # no_op + 4 phrasing, full
        if tr.trace_id in breadth:
            arms += BREADTH_SL                           # + breadth subset
        return arms

    planned = sum(len(arms_for(t)) for t in traces)
    print(f"v2 recovery sweep: SL={len(sl)} (breadth subset {len(breadth)}), SF={len(sf)}  N={n}")
    print(f"planned cells={planned}  ~replays={planned * n}  model={config.model_tag} temp={config.temperature}")

    outcomes: list[ReplayOutcome] = []
    dists: dict[str, dict[str, list[bool]]] = defaultdict(dict)
    done = 0
    for tr in traces:
        task = TASKS[tr.trace_id.split("-r")[0]]
        for arm_name in arms_for(tr):
            sandbox = sweep_dir / tr.trace_id / arm_name
            registry = ToolRegistry([build_v2_tools(sandbox)[t] for t in task.tool_names])
            succ = replay_cell(trace=tr, k=tr.failure_step_k or 0, intervention=_arm(arm_name, task.id),
                               tools=registry, backend=backend, config=config,
                               verifier=task.make_verifier(sandbox), n=n)
            dists[tr.trace_id][arm_name] = succ
            outcomes.append(ReplayOutcome(trace_id=tr.trace_id, failure_class=tr.failure_class or "?",
                                          intervention=arm_name, successes=sum(succ), n=n))
            done += 1
            if done % 25 == 0:
                print(f"  ...{done}/{planned} cells")

    sweep_dir.mkdir(parents=True, exist_ok=True)
    (sweep_dir / "results.json").write_text(json.dumps(
        {"outcomes": [vars(o) for o in outcomes], "distributions": dists}, indent=2), encoding="utf-8")
    _report(outcomes)
    print(f"\nraw results: {sweep_dir/'results.json'}")


def _report(outcomes: list[ReplayOutcome]) -> None:
    print("\n" + "=" * 76 + "\nv2 RECOVERY — DIRECTIONAL. Raw per-cell distributions below.\n" + "=" * 76)
    by_cell: dict[tuple[str, str], list[ReplayOutcome]] = defaultdict(list)
    for o in outcomes:
        by_cell[(o.failure_class, o.intervention)].append(o)
    print(f"\n{'mechanism':<22}{'arm':<34}{'traces':>7}{'recovery':>10}")
    for (mech, arm) in sorted(by_cell):
        cell = by_cell[(mech, arm)]
        print(f"{mech:<22}{arm:<34}{len(cell):>7}{mean_recovery(cell):>10.2f}")

    print("\n--- IATROGENIC vs no_op (paired, strictly worse) ---")
    for mech in sorted({o.failure_class for o in outcomes}):
        ctrl = [o for o in outcomes if o.intervention == CONTROL and o.failure_class == mech]
        if not ctrl:
            print(f"  {mech}: no no_op baseline in this mechanism (surface-form uses full arms)")
        for arm in sorted({o.intervention for o in outcomes} - {CONTROL}):
            arm_o = [o for o in outcomes if o.intervention == arm and o.failure_class == mech]
            paired_ctrl = [o for o in ctrl if o.trace_id in {a.trace_id for a in arm_o}]
            if arm_o and len(paired_ctrl) == len(arm_o):
                print(f"  {mech:<22}{arm:<34}iatro={iatrogenic_rate(arm_o, paired_ctrl):.2f}  "
                      f"net={net_improvement(arm_o, paired_ctrl):+.2f}")

    near = [o for o in outcomes if is_near_boundary(o)]
    print(f"\n--- near-boundary cells (need higher N): {len(near)} ---")


def main() -> None:
    p = argparse.ArgumentParser(description="v2 recovery sweep.")
    p.add_argument("--run", type=Path, default=Path("data/v2batch"))
    p.add_argument("--n", type=int, default=3)
    p.add_argument("--config", type=Path, default=Path("paper-recovery/configs/kill_test.yaml"))
    p.add_argument("--limit", type=int, default=None, help="smoke test: first N traces per mechanism")
    args = p.parse_args()
    run(args.run, args.n, args.config, args.limit)


if __name__ == "__main__":
    main()
