"""Phase 3: the tool-reliability screen — a committed, reproducible implementation.

**Why this file exists.** The original smoke test that produced the recorded numbers
(llama3.1:8b 0/6, mistral:7b 3/6, qwen2.5:7b 6/6) was a throwaway scratchpad script
and was never committed, so those numbers cannot currently be reproduced. Since the
tool-reliability floor is now a paper contribution ("cross-model recovery evaluation
is confounded by tool-capability"), the instrument that establishes it has to be real
code with tests, not a deleted scratch file.

**What it measures.** Multi-step tool CHAINING, which is the capability every recovery
arm depends on: a repair only works if the model can re-issue a tool call and thread
the result forward. Each task needs two calls where the second consumes the first's
numeric output. The characteristic failure this catches is argument-threading breakage
(passing the literal string "result", or re-deriving the number in text instead of
using the tool's return).

**The screening rule is PRE-COMMITTED (see `PASS_THRESHOLD`).** A model is admitted to
the cross-model replication only at 6/6 clean. This is fixed before any candidate is
run so the bar cannot drift toward whatever a promising model happens to score --
the same pre-commitment discipline that kept the Mistral result honest.

**Calibration before use.** `--calibrate` re-screens the three already-recorded models
and checks this implementation reproduces their recorded scores. Because it uses the
real harness runner rather than the original bespoke loop, agreement is not guaranteed
a priori; if the recorded values do not reproduce, the new instrument -- not the old
numbers -- is what needs explaining, and no candidate result should be trusted until
that is resolved.

Usage:
    python paper-recovery/screen_models.py --calibrate
    python paper-recovery/screen_models.py --models llama3.2:latest granite3.3:8b
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from harness.backend import OllamaBackend
from harness.config import Config
from harness.runner import run_agent
from harness.tools import ARITHMETIC_TOOLS, ToolRegistry

# A model must chain cleanly on EVERY task to be admitted. Fixed before any
# candidate is screened; do not lower it to accommodate a near-miss.
PASS_THRESHOLD = 6

# Screening conditions, matched to the original B3 smoke test (LOGBOOK 2026-07-21):
# temperature 0 and seed 7, so a model's score is a property of the model rather
# than of sampling luck.
SCREEN_TEMPERATURE = 0.0
SCREEN_SEED = 7
SCREEN_MAX_TURNS = 6

# Recorded scores from the original (uncommitted) smoke test, used only by
# --calibrate to check that this reimplementation agrees with the published table.
RECORDED = {"qwen2.5:7b": 6, "mistral:7b": 3, "llama3.1:8b": 0}


@dataclass(frozen=True)
class ScreenTask:
    """One two-step chaining task.

    Attributes:
        prompt: The instruction given to the agent.
        answer: The correct final value. Checked as a whole token so that "12"
            does not match inside "120".
        first: The expected first-step numeric result, whose appearance in a later
            tool call is what demonstrates genuine threading.
    """

    prompt: str
    answer: float
    first: float


# Each task requires add-then-multiply or multiply-then-add: the second call cannot
# be made without the first call's returned number.
SCREEN_TASKS: list[ScreenTask] = [
    ScreenTask("Add 17 and 25, then multiply the result by 3. Report the final number.", 126.0, 42.0),
    ScreenTask("Add 8 and 14, then multiply the result by 5. Report the final number.", 110.0, 22.0),
    ScreenTask("Multiply 6 and 7, then add 19 to the result. Report the final number.", 61.0, 42.0),
    ScreenTask("Multiply 12 and 4, then add 33 to the result. Report the final number.", 81.0, 48.0),
    ScreenTask("Add 45 and 55, then multiply the result by 2. Report the final number.", 200.0, 100.0),
    ScreenTask("Multiply 9 and 9, then add 19 to the result. Report the final number.", 100.0, 81.0),
]


def _tokens(text: str) -> set[str]:
    """Numeric-ish tokens in a string, split on non-numeric characters."""
    out, cur = set(), ""
    for ch in text:
        if ch.isdigit() or ch == ".":
            cur += ch
        else:
            if cur:
                out.add(cur.rstrip("."))
            cur = ""
    if cur:
        out.add(cur.rstrip("."))
    return out


def _matches(text: str, value: float) -> bool:
    """Whether `value` appears as a whole numeric token in `text`.

    Whole-token matching (not substring) so that 12 does not match inside 120 --
    the same rule the study's verifiers use.
    """
    targets = {str(value), str(int(value))} if value == int(value) else {str(value)}
    return bool(targets & _tokens(text))


@dataclass
class TaskOutcome:
    """Result of screening one task. `clean` requires BOTH threading and correctness."""

    clean: bool
    correct_answer: bool
    threaded: bool
    n_tool_calls: int
    note: str


def screen_task(task: ScreenTask, backend: OllamaBackend, config: Config) -> TaskOutcome:
    """Run one chaining task and judge whether the model chained cleanly.

    A run is clean only if it (a) makes at least two tool calls, (b) feeds the first
    call's result into a later call, and (c) reports the right final number. Getting
    the answer right by reasoning in text, without threading, is NOT clean: such a
    model cannot be repaired by a tool-based intervention, which is the whole point
    of the screen.
    """
    registry = ToolRegistry(list(ARITHMETIC_TOOLS))
    result = run_agent(
        initial_messages=[{"role": "user", "content": task.prompt}],
        tools=registry,
        backend=backend,
        config=config,
        replay_index=0,
        start_turn=0,
        max_turns=SCREEN_MAX_TURNS,
    )
    calls = [s for s in result.steps if s.tool_name]
    # Threading is evidenced by the first result appearing in a LATER call's args.
    threaded = any(_matches(json.dumps(s.tool_args), task.first) for s in calls[1:])
    correct = _matches(result.final_output, task.answer)
    clean = len(calls) >= 2 and threaded and correct

    if clean:
        note = "clean chain"
    elif not calls:
        note = "no tool call (reasoned in text)"
    elif len(calls) < 2:
        note = "single tool call only"
    elif not threaded:
        note = "failed to thread first result into second call"
    else:
        note = "threaded but wrong final answer"
    return TaskOutcome(clean, correct, threaded, len(calls), note)


def screen_model(model_tag: str, host: str, verbose: bool = True) -> dict:
    """Screen one model across all tasks and return its record."""
    config = Config(ollama_host=host, model_tag=model_tag, seed=SCREEN_SEED,
                    temperature=SCREEN_TEMPERATURE, max_turns=SCREEN_MAX_TURNS)
    backend = OllamaBackend(config.model_tag, config.ollama_host)
    outcomes = []
    for i, task in enumerate(SCREEN_TASKS):
        outcome = screen_task(task, backend, config)
        outcomes.append(outcome)
        if verbose:
            mark = "OK " if outcome.clean else "FAIL"
            print(f"    task {i + 1}: {mark} calls={outcome.n_tool_calls} "
                  f"threaded={outcome.threaded} correct={outcome.correct_answer} "
                  f"({outcome.note})")
    clean = sum(o.clean for o in outcomes)
    return {
        "model": model_tag,
        "clean": clean,
        "total": len(SCREEN_TASKS),
        "admitted": clean >= PASS_THRESHOLD,
        "correct_but_untied": sum(o.correct_answer and not o.threaded for o in outcomes),
        "no_tool_call": sum(o.n_tool_calls == 0 for o in outcomes),
        "notes": [o.note for o in outcomes],
    }


def run(models: list[str], host: str, out_path: Path | None) -> None:
    """Screen each model, print the table, and record the results."""
    print(f"TOOL-RELIABILITY SCREEN — pre-committed threshold: {PASS_THRESHOLD}/"
          f"{len(SCREEN_TASKS)} clean chains")
    print(f"conditions: temperature={SCREEN_TEMPERATURE} seed={SCREEN_SEED} "
          f"max_turns={SCREEN_MAX_TURNS}\n")

    records = []
    for model in models:
        print(f"  screening {model} ...")
        try:
            record = screen_model(model, host)
        except Exception as exc:  # noqa: BLE001 - a failed model must not abort the sweep
            print(f"    ERROR: {exc}")
            records.append({"model": model, "clean": None, "error": repr(exc)})
            continue
        records.append(record)
        verdict = "ADMITTED" if record["admitted"] else "rejected"
        print(f"    -> {record['clean']}/{record['total']} clean  [{verdict}]\n")

    print("=" * 64)
    print(f"{'model':<24}{'clean':<10}{'verdict':<12}notes")
    for r in records:
        if r.get("clean") is None:
            print(f"{r['model']:<24}{'ERROR':<10}{'-':<12}{r.get('error', '')[:40]}")
            continue
        verdict = "ADMITTED" if r["admitted"] else "rejected"
        extra = f"no-tool-call={r['no_tool_call']} untied-correct={r['correct_but_untied']}"
        print(f"{r['model']:<24}{r['clean']}/{r['total']:<8}{verdict:<12}{extra}")

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(
            {"threshold": PASS_THRESHOLD, "temperature": SCREEN_TEMPERATURE,
             "seed": SCREEN_SEED, "records": records}, indent=2), encoding="utf-8")
        print(f"\nwritten: {out_path}")


def calibrate(host: str) -> None:
    """Re-screen the already-recorded models and check this code reproduces them."""
    print("CALIBRATION — does this implementation reproduce the recorded scores?\n")
    ok = True
    for model, expected in RECORDED.items():
        print(f"  {model} (recorded {expected}/6) ...")
        try:
            got = screen_model(model, host, verbose=False)["clean"]
        except Exception as exc:  # noqa: BLE001
            print(f"    ERROR: {exc}")
            ok = False
            continue
        agree = "AGREES" if got == expected else "DISAGREES"
        if got != expected:
            ok = False
        print(f"    got {got}/6 — {agree}\n")
    print("=" * 64)
    if ok:
        print("Calibration PASSED. Candidate screening results can be compared to the "
              "published table.")
    else:
        print("Calibration FAILED. Do NOT trust candidate scores from this instrument "
              "until the disagreement is explained: either the recorded numbers or this "
              "implementation is wrong, and which one matters for the paper's Table 5.")


def main() -> None:
    p = argparse.ArgumentParser(description="Phase 3 tool-reliability screen.")
    p.add_argument("--models", nargs="*", default=[], help="model tags to screen")
    p.add_argument("--calibrate", action="store_true",
                   help="re-screen the recorded models to validate this implementation")
    p.add_argument("--host", default="http://localhost:11434")
    p.add_argument("--out", type=Path, default=Path("data/screening/results.json"))
    args = p.parse_args()

    if args.calibrate:
        calibrate(args.host)
    if args.models:
        run(args.models, args.host, args.out)
    if not args.calibrate and not args.models:
        p.error("give --calibrate, --models, or both")


if __name__ == "__main__":
    main()
