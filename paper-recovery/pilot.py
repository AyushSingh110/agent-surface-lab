"""Pilot driver: generate a small batch of runs to MEASURE real failure rates
before committing the full batch. It saves traces for the human to label — it
NEVER assigns a failure class (CLAUDE.md §3; class labeling is the human's, code
only computes the deterministic `answer_correct`).

What it reports: failure rate by INTENDED class (each task's design target). The
realized-class hit-rate needs the human labeling pass and is not produced here.

Usage (from repo root, `surface` env active):
    python paper-recovery/pilot.py --per-class 4 --out data/pilot

Run only after the fixtures/GT are approved. Requires a live Ollama server.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from harness.backend import OllamaBackend
from harness.config import load_config
from harness.recorder import append_trace, build_trace, now_iso
from harness.runner import run_agent
from harness.tools import ToolRegistry
from recovery_sandbox.tasks import KILL_TEST_TASKS, TaskSpec, tasks_by_class
from recovery_sandbox.tools import build_tools

_SYSTEM_PROMPT = (
    "You are a task-completing agent. Use the provided tools to accomplish the user's "
    "task, one tool call at a time. When the task is fully done, reply with your final "
    "answer in plain text and no tool call."
)


def _select_tasks(per_class: int) -> list[TaskSpec]:
    """Stratified selection: the first `per_class` tasks of each intended class."""
    selected: list[TaskSpec] = []
    for tasks in tasks_by_class().values():
        selected.extend(tasks[:per_class])
    return selected


def run_pilot(per_class: int, out_dir: Path, config_yaml: Path | None) -> None:
    config = load_config(config_yaml)
    backend = OllamaBackend(model_tag=config.model_tag, host=config.ollama_host)
    traces_path = out_dir / "traces.jsonl"

    tallies: dict[str, list[bool]] = defaultdict(list)  # intended_class -> [answer_correct...]
    failing_ids: list[str] = []

    for run_index, task in enumerate(_select_tasks(per_class)):
        sandbox_dir = out_dir / "runs" / f"{task.id}-r{run_index}"
        tool_map = build_tools(sandbox_dir)
        registry = ToolRegistry([tool_map[name] for name in task.tool_names])
        initial_messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": task.prompt},
        ]
        ts_start = now_iso()
        # replay_index=run_index offsets the seed so runs differ but stay reproducible.
        result = run_agent(
            initial_messages=initial_messages,
            tools=registry,
            backend=backend,
            config=config,
            replay_index=run_index,
        )
        trace = build_trace(
            trace_id=f"{task.id}-r{run_index}",
            task=task.prompt,
            task_class=task.intended_class,  # DESIGN target, not a realized-class label
            system_prompt=_SYSTEM_PROMPT,
            initial_messages=initial_messages,
            steps=result.steps,
            final_output=result.final_output,
            model_tag=backend.model_tag,
            seed=config.seed,
            temperature=config.temperature,
            ts_start=ts_start,
            requirement=task.requirement,
        )
        # Verify with the real trace: the HL fabrication check reads trace.task.
        answer_correct = task.make_verifier(sandbox_dir)(trace, result.final_output)
        trace.answer_correct = answer_correct  # deterministic; failure_class stays None
        append_trace(trace, traces_path)

        tallies[task.intended_class].append(answer_correct)
        if not answer_correct:
            failing_ids.append(trace.trace_id)
        print(f"[{trace.trace_id}] intended={task.intended_class} "
              f"answer_correct={answer_correct} stop={result.stopped_reason}")

    _print_summary(tallies, failing_ids, traces_path)


def _print_summary(tallies: dict[str, list[bool]], failing_ids: list[str], traces_path: Path) -> None:
    print("\n=== PILOT SUMMARY (failure rate by INTENDED class; NOT a realized-class label) ===")
    total = fails = 0
    for cls in sorted(tallies):
        results = tallies[cls]
        n = len(results)
        f = sum(1 for r in results if not r)
        total += n
        fails += f
        print(f"  {cls:<20} runs={n:2d}  failed={f:2d}  failure_rate={f / n:.2f}")
    print(f"  {'TOTAL':<20} runs={total:2d}  failed={fails:2d}")
    print(f"\nFailing traces saved for labeling ({len(failing_ids)}): {traces_path}")
    print("NEXT (human): label failure_class + oracle failure_step_k on the FAILING traces only.")
    print("Code did NOT assign any failure class.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Recovery kill-test pilot generator.")
    parser.add_argument("--per-class", type=int, default=4,
                        help="Tasks per intended class to run (default 4 -> ~20 runs).")
    parser.add_argument("--out", type=Path, default=Path("data/pilot"),
                        help="Output dir for traces + per-run sandboxes (gitignored).")
    parser.add_argument("--config", type=Path, default=Path("paper-recovery/configs/kill_test.yaml"),
                        help="Run config YAML.")
    args = parser.parse_args()
    run_pilot(args.per_class, args.out, args.config)


if __name__ == "__main__":
    main()
