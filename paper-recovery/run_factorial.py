"""Phase 2: the repair-surface factorial -- identifying what `action-licensing` is.

**The problem this run exists to solve.** The action-licensing claim currently rests on
one contrast: `req_declarative_lookup_permitting` (1.00) vs `req_declarative_neutral`
(0.16). But those two sentences differ in FOUR ways at once -- the winner grants
permission, names tools, adds length, and adds a second clause. Any of the four could
carry the effect, so "licensing" is not identified. A reviewer can dismiss C2 in one
sentence ("you primed it with the word 'tools'"), and they would be right to.

**The design.** All five arms below share the identical base `Report {core}`, so the
base is held constant and only the trailing clause varies. Crossing licensing against
tool-mention gives a 2x2, plus a no-clause control:

                    | mentions tools    | no tool mention
    ----------------+-------------------+---------------------
    licenses action | lookup_permitting | license_no_tool
    no licensing    | tool_no_license   | placebo (length-matched)
    no clause       | --                | imperative_plain

`req_imperative_plain` ("Report {core}.") and `req_declarative_lookup_permitting`
("Report {core}; use tools to verify.") were ALREADY run at N=10 in the firm-up, so
only the three new arms need replays: 3 arms x 50 traces x N=10 = ~1500.

**Every outcome is publishable, which is why this is worth running.**
  - `license_no_tool` high AND `tool_no_license` low -> action-licensing confirmed and
    identified; C2 becomes bulletproof.
  - `tool_no_license` high AND `license_no_tool` low -> C2 is REFUTED and replaced by
    tool-mention priming: the agent responds to a lexical trigger, not a semantic
    permission. That is a stronger result for the surface-cue thesis, not a weaker one.
  - `placebo` high -> any second clause works; the effect is attention/salience, not
    content. Also a real finding, and a caution for the prompt-engineering literature.

The point estimates alone will not settle this -- read the output together with the
paired bootstrap contrasts (`analysis_factorial.py`), especially each arm against
`placebo`, which is the length-matched control that isolates clause CONTENT.

Usage:
    python paper-recovery/run_factorial.py --run data/v2batch --n 10
Requires labels.json and a live Ollama server. Resumes from its checkpoint on restart.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from harness.backend import OllamaBackend
from harness.config import load_config
from harness.replay import InterventionOutcome, reconstruct, replay_cell
from harness.tools import ToolRegistry
from harness.trace import TraceRecord
from recovery_sandbox.v2_tasks import REQUIREMENT_CORES, V2_TASKS
from recovery_sandbox.v2_tools import build_v2_tools

TASKS = {t.id: t for t in V2_TASKS}
DEPTH = {t.id: t.trigger_depth for t in V2_TASKS}

# The three NEW arms. Each is `Report {core};` plus one trailing clause, so the only
# thing that varies across the factorial is that clause. `licenses` and `mentions_tools`
# record the factor levels so the analysis never has to re-derive them from the text.
FACTORIAL_ARMS: dict[str, dict] = {
    "fac_license_no_tool": {
        "template": "Report {core}; take another step to check first.",
        "licenses": True,
        "mentions_tools": False,
    },
    "fac_tool_no_license": {
        "template": "Report {core}; tools were available for this task.",
        "licenses": False,
        "mentions_tools": True,
    },
    "fac_placebo": {
        "template": "Report {core}; this is an important requirement.",
        "licenses": False,
        "mentions_tools": False,
    },
}

# Already run at N=10 in the firm-up; listed so the analysis can complete the 2x2
# without re-running them. Do NOT re-run these here -- reusing the existing cells keeps
# the comparison on identical replays rather than a fresh sample.
EXISTING_ARMS = {
    "req_declarative_lookup_permitting": {"licenses": True, "mentions_tools": True},
    "req_imperative_plain": {"licenses": False, "mentions_tools": False, "no_clause": True},
}


def _arm(name: str, task_id: str):
    """Build the intervention closure for one factorial arm."""
    sentence = FACTORIAL_ARMS[name]["template"].format(core=REQUIREMENT_CORES[task_id])

    def _f(trace: TraceRecord, k: int, config) -> InterventionOutcome:
        msgs = reconstruct(trace, k)
        # Identical wrapper to the firm-up phrasing arms, so the only difference
        # between this run and those cells is the requirement sentence itself.
        msgs.append({"role": "user", "content": f"You must satisfy this requirement: {sentence}"})
        return InterventionOutcome(msgs, k, name, sentence)

    return _f


def _load_skipped_lookup(run_dir: Path) -> list[TraceRecord]:
    """Load the labeled skipped-lookup traces (the pool C2 rests on)."""
    labels = json.loads((run_dir / "labels.json").read_text(encoding="utf-8-sig"))
    traces = {
        t.trace_id: t
        for t in (
            TraceRecord.from_json_line(line)
            for line in (run_dir / "traces.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    out = []
    for tid, lab in labels.items():
        if lab["failure_class"] != "skipped_lookup":
            continue
        tr = traces[tid]
        tr.failure_class = lab["failure_class"]
        tr.failure_step_k = int(lab["failure_step_k"])
        out.append(tr)
    return out


def run(run_dir: Path, n: int, config_yaml: Path | None) -> None:
    """Run the three new factorial arms over every labeled skipped-lookup trace."""
    config = load_config(config_yaml)
    backend = OllamaBackend(config.model_tag, config.ollama_host)
    traces = _load_skipped_lookup(run_dir)
    arms = list(FACTORIAL_ARMS)
    total = len(traces) * len(arms)
    print(f"FACTORIAL N={n}: {len(traces)} skipped-lookup traces x {len(arms)} new arms")
    print(f"cells={total}  ~replays={total * n}  model={config.model_tag}")
    for name, spec in FACTORIAL_ARMS.items():
        print(f"  {name:<24} licenses={spec['licenses']!s:<6} "
              f"tools={spec['mentions_tools']!s:<6} \"{spec['template']}\"")

    outdir = run_dir / "recovery_factorial"
    outdir.mkdir(parents=True, exist_ok=True)
    cells_path = outdir / "cells.jsonl"

    # Same crash-resilience contract as run_recovery_firm: checkpoint every cell so an
    # Ollama disconnect mid-run costs one cell, not the whole sweep.
    done_cells: set[tuple[str, str]] = set()
    if cells_path.is_file():
        for line in cells_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                done_cells.add((rec["trace_id"], rec["intervention"]))
        print(f"resuming: {len(done_cells)} cells already done")

    done = len(done_cells)
    with cells_path.open("a", encoding="utf-8") as ckpt:
        for tr in traces:
            task = TASKS[tr.trace_id.split("-r")[0]]
            for arm in arms:
                if (tr.trace_id, arm) in done_cells:
                    continue
                sandbox = outdir / tr.trace_id / arm
                registry = ToolRegistry([build_v2_tools(sandbox)[t] for t in task.tool_names])
                successes = replay_cell(
                    trace=tr, k=tr.failure_step_k or 0, intervention=_arm(arm, task.id),
                    tools=registry, backend=backend, config=config,
                    verifier=task.make_verifier(sandbox), n=n,
                )
                ckpt.write(json.dumps({
                    "trace_id": tr.trace_id, "intervention": arm,
                    "failure_class": tr.failure_class,
                    "depth": DEPTH[task.id],
                    "licenses": FACTORIAL_ARMS[arm]["licenses"],
                    "mentions_tools": FACTORIAL_ARMS[arm]["mentions_tools"],
                    "successes": sum(successes), "n": n, "dist": successes,
                }) + "\n")
                ckpt.flush()
                done += 1
                if done % 25 == 0:
                    print(f"  ...{done}/{total} cells")

    print(f"\ndone: {done}/{total} cells -> {cells_path}")
    print("next: python paper-recovery/analysis_factorial.py --run", run_dir)


def main() -> None:
    p = argparse.ArgumentParser(description="Phase 2 repair-surface factorial.")
    p.add_argument("--run", type=Path, default=Path("data/v2batch"))
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--config", type=Path, default=Path("paper-recovery/configs/kill_test.yaml"))
    args = p.parse_args()
    run(args.run, args.n, args.config)


if __name__ == "__main__":
    main()
