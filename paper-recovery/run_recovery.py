"""Recovery kill-test driver: the first time an intervention is applied to a trace.

Runs the full cell sweep over the HUMAN-LABELED failing traces:
    traces x {no_op, reflect_and_retry, rollback_2, requirement_injection} x N replays

Reports, per (intervention x mechanism) cell: the recovery DISTRIBUTION over N (never
collapsed to a bare point estimate), the paired iatrogenic rate vs the no_op control,
net improvement, and which cells sit near a decision boundary and need a higher N.

IMPORTANT — this is a KILL TEST, not a result. With a handful of traces every number
is DIRECTIONAL. A null (all interventions indistinguishable) is a legitimate and
valuable outcome and is reported plainly, not massaged.

Labels come from a human-filled JSON file; this script NEVER assigns a failure class.
Requires: data/<run>/labels.json mapping trace_id -> {failure_class, failure_step_k}.

Usage (from repo root, `surface` env, Ollama running):
    python paper-recovery/run_recovery.py --run data/repilot --n 3
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from harness.backend import OllamaBackend
from harness.config import load_config
from harness.interventions import KILL_TEST_INTERVENTIONS
from harness.metrics import (
    ReplayOutcome,
    is_near_boundary,
    iatrogenic_rate,
    mean_recovery,
    net_improvement,
)
from harness.replay import replay_cell
from harness.tools import ToolRegistry
from harness.trace import TraceRecord
from recovery_sandbox.tasks import KILL_TEST_TASKS
from recovery_sandbox.tools import build_tools

TASKS = {t.id: t for t in KILL_TEST_TASKS}
CONTROL = "no_op"


def _load_labeled(run_dir: Path) -> list[TraceRecord]:
    """Load traces and merge the human labels; fail loudly if labels are missing."""
    labels_path = run_dir / "labels.json"
    if not labels_path.is_file():
        raise FileNotFoundError(
            f"no labels at {labels_path} — the human must label failure_class and "
            f"failure_step_k before any recovery run (code never assigns a class)"
        )
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    with (run_dir / "traces.jsonl").open(encoding="utf-8") as fh:
        traces = {t.trace_id: t for t in (TraceRecord.from_json_line(l) for l in fh if l.strip())}

    out: list[TraceRecord] = []
    for trace_id, lab in labels.items():
        cls, k = lab.get("failure_class"), lab.get("failure_step_k")
        if not cls or k is None:
            raise ValueError(f"{trace_id}: labels.json needs both failure_class and failure_step_k")
        tr = traces[trace_id]
        tr.failure_class = cls
        tr.failure_step_k = int(k)
        if not 0 <= tr.failure_step_k <= len(tr.steps):
            raise ValueError(f"{trace_id}: failure_step_k={k} out of range for {len(tr.steps)} steps")
        out.append(tr)
    return out


def run_sweep(run_dir: Path, n: int, config_yaml: Path | None) -> None:
    config = load_config(config_yaml)
    backend = OllamaBackend(model_tag=config.model_tag, host=config.ollama_host)
    traces = _load_labeled(run_dir)
    sweep_dir = run_dir / "recovery"

    # trace_id -> intervention -> per-replay success booleans (the raw distribution).
    dists: dict[str, dict[str, list[bool]]] = defaultdict(dict)
    outcomes: list[ReplayOutcome] = []

    total = len(traces) * len(KILL_TEST_INTERVENTIONS) * n
    print(f"sweep: {len(traces)} traces x {len(KILL_TEST_INTERVENTIONS)} interventions x N={n} "
          f"= {total} replays   model={config.model_tag} temp={config.temperature} seed={config.seed}")

    for tr in traces:
        task = TASKS[tr.trace_id.split("-r")[0]]
        for name, intervention in KILL_TEST_INTERVENTIONS.items():
            # All kill-test traces are non-file tasks, so one sandbox per cell is safe;
            # a file-deliverable task would need a fresh sandbox per replay.
            sandbox = sweep_dir / tr.trace_id / name
            tool_map = build_tools(sandbox)
            registry = ToolRegistry([tool_map[t] for t in task.tool_names])
            successes = replay_cell(
                trace=tr,
                k=tr.failure_step_k or 0,
                intervention=intervention,
                tools=registry,
                backend=backend,
                config=config,
                verifier=task.make_verifier(sandbox),
                n=n,
            )
            dists[tr.trace_id][name] = successes
            outcomes.append(ReplayOutcome(
                trace_id=tr.trace_id, failure_class=tr.failure_class or "unlabeled",
                intervention=name, successes=sum(successes), n=n,
            ))
            pattern = "".join("R" if s else "F" for s in successes)  # per-replay R/F
            print(f"  [{tr.trace_id}] {name:<22} {pattern}  rate={sum(successes)}/{n}")

    _report(outcomes, dists, n)
    _save(sweep_dir, outcomes, dists)


def _report(outcomes: list[ReplayOutcome], dists: dict[str, dict[str, list[bool]]], n: int) -> None:
    by_cell: dict[tuple[str, str], list[ReplayOutcome]] = defaultdict(list)
    for o in outcomes:
        by_cell[(o.intervention, o.failure_class)].append(o)

    print("\n" + "=" * 74)
    print("RECOVERY KILL TEST — DIRECTIONAL ONLY (tiny n; not a result)")
    print("=" * 74)
    print(f"\n{'intervention':<24}{'mechanism':<24}{'traces':>7}{'recovery':>11}")
    for (interv, mech) in sorted(by_cell):
        cell = by_cell[(interv, mech)]
        rates = [f"{o.successes}/{o.n}" for o in cell]
        print(f"{interv:<24}{mech:<24}{len(cell):>7}{mean_recovery(cell):>11.2f}   [{', '.join(rates)}]")

    print("\n--- IATROGENIC RATE (paired, strictly worse than no_op) ---")
    mechanisms = sorted({o.failure_class for o in outcomes})
    for mech in mechanisms:
        control = [o for o in outcomes if o.intervention == CONTROL and o.failure_class == mech]
        for interv in sorted({o.intervention for o in outcomes} - {CONTROL}):
            arm = [o for o in outcomes if o.intervention == interv and o.failure_class == mech]
            if not arm or not control:
                continue
            print(f"  {mech:<24}{interv:<24}"
                  f"iatrogenic={iatrogenic_rate(arm, control):.2f}  "
                  f"net_vs_noop={net_improvement(arm, control):+.2f}")

    near = [o for o in outcomes if is_near_boundary(o)]
    print(f"\n--- CELLS NEAR A DECISION BOUNDARY (would need higher N): {len(near)} ---")
    for o in near:
        print(f"  {o.trace_id:<14}{o.intervention:<24}{o.successes}/{o.n}")

    print("\nREAD THIS AS: does anything MOVE? If all arms (including no_op) recover at "
          "indistinguishable\nrates, that is a NULL result and must be reported as such.")


def _save(sweep_dir: Path, outcomes: list[ReplayOutcome], dists: dict) -> None:
    sweep_dir.mkdir(parents=True, exist_ok=True)
    path = sweep_dir / "results.json"
    payload = {
        "outcomes": [vars(o) for o in outcomes],
        "distributions": dists,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nraw results saved: {path}")


def main() -> None:
    p = argparse.ArgumentParser(description="Recovery kill-test cell sweep.")
    p.add_argument("--run", type=Path, default=Path("data/repilot"), help="Run dir with traces + labels.json")
    p.add_argument("--n", type=int, default=3, help="Replays per cell (default 3)")
    p.add_argument("--config", type=Path, default=Path("paper-recovery/configs/kill_test.yaml"))
    args = p.parse_args()
    run_sweep(args.run, args.n, args.config)


if __name__ == "__main__":
    main()
