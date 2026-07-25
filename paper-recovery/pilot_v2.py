"""v2 generation pilot: measure the HIT RATE of each v2 task shape before the full
batch. No interventions here — this only generates runs and scores answer_correct
deterministically, exactly like the v1 pilot, so we learn which task shapes reliably
induce their mechanism on qwen2.5:7b.

Reports hit rate (induced-failure rate) by task and by mechanism, and by
trigger_depth (the detection-lateness axis). Never labels a realized class — that is
the human's pass. Failing traces are saved for later labeling + the recovery sweep.

Usage: python paper-recovery/pilot_v2.py --repeats 3 --out data/v2pilot
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from harness.backend import OllamaBackend
from harness.config import load_config
from harness.recorder import append_trace, build_trace, now_iso
from harness.runner import run_agent
from harness.tools import ToolRegistry
from recovery_sandbox.v2_tasks import V2_TASKS, V2Task
from recovery_sandbox.v2_tools import build_v2_tools

_SYSTEM_PROMPT = (
    "You are a task-completing agent. Use the provided tools to accomplish the user's "
    "task, one tool call at a time. When the task is fully done, reply with your final "
    "answer in plain text and no tool call."
)


@dataclass
class _Outcome:
    correct: bool
    budget: bool


def run_v2_pilot(repeats: int, per_family: int | None, out_dir: Path, config_yaml: Path | None) -> None:
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    config = load_config(config_yaml)
    backend = OllamaBackend(config.model_tag, config.ollama_host)
    traces_path = out_dir / "traces.jsonl"

    tasks = V2_TASKS if per_family is None else _first_per_family(per_family)
    by_task: dict[str, list[_Outcome]] = defaultdict(list)
    by_mech: dict[str, list[_Outcome]] = defaultdict(list)
    by_depth: dict[int, list[_Outcome]] = defaultdict(list)
    failing: list[str] = []
    run_index = 0

    for task in tasks:
        for _ in range(repeats):
            sandbox = out_dir / "runs" / f"{task.id}-r{run_index}"
            registry = ToolRegistry([build_v2_tools(sandbox)[t] for t in task.tool_names])
            init = [{"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": task.prompt}]
            ts = now_iso()
            res = run_agent(initial_messages=init, tools=registry, backend=backend,
                            config=config, replay_index=run_index)
            trace = build_trace(
                trace_id=f"{task.id}-r{run_index}", task=task.prompt, task_class=task.mechanism,
                system_prompt=_SYSTEM_PROMPT, initial_messages=init, steps=res.steps,
                final_output=res.final_output, model_tag=backend.model_tag, seed=config.seed,
                temperature=config.temperature, ts_start=ts, requirement=task.requirement)
            correct = task.make_verifier(sandbox)(trace, res.final_output)
            trace.answer_correct = correct
            trace.stopped_reason = res.stopped_reason
            append_trace(trace, traces_path)

            o = _Outcome(correct, res.stopped_reason == "max_turns")
            by_task[task.id].append(o)
            by_mech[task.mechanism].append(o)
            by_depth[task.trigger_depth].append(o)
            if not correct:
                failing.append(trace.trace_id)
            print(f"[{trace.trace_id}] mech={task.mechanism} depth={task.trigger_depth} "
                  f"correct={correct} stop={res.stopped_reason}")
            run_index += 1

    _summary(by_task, by_mech, by_depth, failing, traces_path, {t.id: t for t in tasks})


def _first_per_family(n: int) -> list[V2Task]:
    seen: dict[str, int] = defaultdict(int)
    out = []
    for t in V2_TASKS:
        if seen[t.mechanism] < n:
            out.append(t)
            seen[t.mechanism] += 1
    return out


def _hit(outs: list[_Outcome]) -> str:
    n = len(outs)
    induced = sum(1 for o in outs if not o.correct and not o.budget)
    budget = sum(1 for o in outs if o.budget)
    return f"induced_fail={induced}/{n} ({induced/n:.2f})  budget={budget}"


def _summary(by_task, by_mech, by_depth, failing, traces_path, taskmap) -> None:
    print("\n=== v2 PILOT HIT RATES (induced-failure rate; realized class = human's later) ===")
    print("\nBy MECHANISM:")
    for m in sorted(by_mech):
        print(f"  {m:22} {_hit(by_mech[m])}")
    print("\nBy TRIGGER DEPTH (detection-lateness axis):")
    for d in sorted(by_depth):
        print(f"  depth={d}  {_hit(by_depth[d])}")
    print("\nBy TASK:")
    for tid in sorted(by_task):
        print(f"  {tid:7} {taskmap[tid].mechanism:20} depth={taskmap[tid].trigger_depth}  {_hit(by_task[tid])}")
    print(f"\nFailing traces saved for labeling + recovery sweep ({len(failing)}): {traces_path}")
    print("Code assigned NO realized class.")


def main() -> None:
    p = argparse.ArgumentParser(description="v2 generation pilot (hit-rate measurement).")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--per-family", type=int, default=None, help="limit to first N tasks per mechanism")
    p.add_argument("--out", type=Path, default=Path("data/v2pilot"))
    p.add_argument("--config", type=Path, default=Path("paper-recovery/configs/kill_test.yaml"))
    args = p.parse_args()
    run_v2_pilot(args.repeats, args.per_family, args.out, args.config)


if __name__ == "__main__":
    main()
