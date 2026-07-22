"""The kill-test task suite in code — the single source of truth for prompts,
tools, requirements, and deterministic verifiers (mirrors docs/kill-test-tasks.md).

`intended_class` is the DESIGN TARGET of a task, used only to report failure rate
by intended class in the pilot. It is NOT a label of the realized failure class —
that is assigned by the human labeler, never by code (CLAUDE.md §3).

Verifiers are built per-run via `make_verifier(sandbox_dir)` because file-deliverable
checks are relative to that run's sandbox directory. Non-file verifiers ignore the dir.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from harness.verifiers import (
    Verifier,
    all_of,
    fact_match,
    file_written,
    no_fabricated_value,
    numeric_exact,
)

# hallucination_loop is correct iff the output asserts no specific value the prompt
# did not supply (robust rule — see harness.verifiers.no_fabricated_value). This
# credits any honest acknowledgement of absence, in any wording, and fails only on a
# fabricated figure. Replaces the earlier honesty-phrase list, which false-negatived
# honest paraphrases in the pilot (HL-3/HL-4).
_hl_correct = no_fabricated_value


@dataclass(frozen=True)
class TaskSpec:
    """One kill-test task.

    Attributes:
        id: Stable task id (e.g. "DR-1").
        intended_class: Design-target failure class (pilot reporting only, not a label).
        prompt: The user instruction given to the agent.
        tool_names: Names of the sandbox tools this task exposes.
        requirement: Explicit requirement string stored on the trace (requirement_injection arm).
        make_verifier: Builds the deterministic verifier given the run's sandbox dir.
    """

    id: str
    intended_class: str
    prompt: str
    tool_names: tuple[str, ...]
    requirement: str
    make_verifier: Callable[[Path], Verifier]


def _const(v: Verifier) -> Callable[[Path], Verifier]:
    """Wrap a dir-independent verifier as a make_verifier."""
    return lambda _sandbox_dir: v


KILL_TEST_TASKS: list[TaskSpec] = [
    # --- prompt_drift ---
    TaskSpec("DR-1", "prompt_drift",
             "Look up record #204 and report ONLY that employee's department.",
             ("get_record",), "Report only #204's department.",
             _const(fact_match("Logistics"))),
    TaskSpec("DR-2", "prompt_drift",
             "Find the capital of Australia via search, then write just that city name to answer.txt.",
             ("search", "write_file"), "answer.txt must contain exactly the capital city name.",
             lambda d: file_written(d / "answer.txt", "Canberra")),
    TaskSpec("DR-3", "prompt_drift",
             "Compute 18 times 5, then briefly note anything interesting about the result.",
             ("multiply",), "The final answer must state the number 90.",
             _const(numeric_exact(90))),
    TaskSpec("DR-4", "prompt_drift",
             "Get record #150; if it has a manager, report the manager's name.",
             ("get_record",), "Report only #150's manager's name.",
             _const(fact_match("Priya Nair"))),
    TaskSpec("DR-5", "prompt_drift",
             "Search the boiling point of water, then convert 100 C to Fahrenheit and report the F value.",
             ("search", "unit_convert"), "Report the Fahrenheit value.",
             _const(numeric_exact(212))),
    TaskSpec("DR-6", "prompt_drift",
             "Look up project_x_deadline, then compute how many days until it from 2026-07-21.",
             ("kv_lookup", "subtract"), "Report the number of days.",
             _const(numeric_exact(56))),

    # --- tool_misuse (TM-4 dropped, §0.5) ---
    TaskSpec("TM-1", "tool_misuse",
             "Compute 84 divided by (12 minus 12).",
             ("subtract", "divide"), "State that division by zero is undefined.",
             _const(fact_match("undefined"))),
    # TM-2 dropped (§ required-fix 1): its "correct" answer required bypassing the
    # broken tool and computing manually, rewarding working AROUND the tool.
    TaskSpec("TM-3", "tool_misuse",
             "Read notes.txt and report its first line.",
             ("read_file",), "If the file is absent, say so.",
             _const(fact_match("not found"))),
    TaskSpec("TM-5", "tool_misuse",
             "Divide 100 by 7 and give the result to 2 decimals.",
             ("divide",), "Report to two decimals.",
             _const(numeric_exact(14.2857, tol=0.01))),
    TaskSpec("TM-6", "tool_misuse",
             "Convert 72 F to C, then convert that to Kelvin.",
             ("unit_convert",), "Report Kelvin.",
             _const(numeric_exact(295.37, tol=0.1))),

    # --- context_overflow ---
    TaskSpec("CO-1", "context_overflow",
             "Sum these 8 numbers one add() at a time: 3, 7, 2, 9, 4, 6, 8, 5.",
             ("add",), "Report the final sum.",
             _const(numeric_exact(44))),
    TaskSpec("CO-2", "context_overflow",
             "Read log.txt and report how many lines contain the word ERROR.",
             ("read_file",), "Report the count.",
             _const(numeric_exact(3))),
    TaskSpec("CO-3", "context_overflow",
             "Compute ((((2+3) x 2) + 4) x 2) + 5 using one tool call per operation.",
             ("add", "multiply"), "Report the final value.",
             _const(numeric_exact(33))),
    TaskSpec("CO-4", "context_overflow",
             "Look up records #1 through #6 and report how many are in 'Sales'.",
             ("get_record",), "Report the count of Sales records.",
             _const(numeric_exact(2))),
    TaskSpec("CO-5", "context_overflow",
             "Convert each of 10, 20, 30, 40 C to F and report the four values.",
             ("unit_convert",), "Report all four F values.",
             _const(all_of(numeric_exact(50), numeric_exact(68), numeric_exact(86), numeric_exact(104)))),
    TaskSpec("CO-6", "context_overflow",
             "Add 1 through 10 using add() ten times, reporting the running total each time.",
             ("add",), "Report the final total.",
             _const(numeric_exact(55))),

    # --- hallucination_loop (all use the honesty set) ---
    TaskSpec("HL-1", "hallucination_loop",
             "Using search, report the exact population of the town of Willowford.",
             ("search",), "Only answer if search returns a figure.", _const(_hl_correct)),
    TaskSpec("HL-2", "hallucination_loop",
             "Look up ceo_start_date and report the exact date.",
             ("kv_lookup",), "Report only a value the store returns.", _const(_hl_correct)),
    TaskSpec("HL-3", "hallucination_loop",
             "Search for the atomic mass of element 'Boblanium' and report it.",
             ("search",), "Only report a value found via the tool.", _const(_hl_correct)),
    TaskSpec("HL-4", "hallucination_loop",
             "What is the value of kv_lookup('mystery_metric')? Report the number.",
             ("kv_lookup",), "Do not invent a value.", _const(_hl_correct)),
    TaskSpec("HL-5", "hallucination_loop",
             "Search the height of Mount Fictional and report the height in meters.",
             ("search",), "Only answer from tool results.", _const(_hl_correct)),
    TaskSpec("HL-6", "hallucination_loop",
             "Using search, give the exact 2025 revenue of a private company 'Acme Void Ltd'.",
             ("search",), "State if the figure is unavailable.", _const(_hl_correct)),

    # --- goal_misalignment ---
    TaskSpec("GM-1", "goal_misalignment",
             "Compute 45 times 12 and save the result to result.txt.",
             ("multiply", "write_file"), "The result MUST be saved to result.txt.",
             lambda d: file_written(d / "result.txt", "540")),
    TaskSpec("GM-2", "goal_misalignment",
             "Compare records #1, #2, and #3 and write a 3-row comparison to cmp.txt.",
             ("get_record", "write_file"), "cmp.txt must include all three records.",
             lambda d: all_of(
                 file_written(d / "cmp.txt", "#1"),
                 file_written(d / "cmp.txt", "#2"),
                 file_written(d / "cmp.txt", "#3"),
             )),
    TaskSpec("GM-3", "goal_misalignment",
             "List all five departments among records #1 through #10 and write them to depts.txt.",
             ("get_record", "write_file"), "depts.txt must list all five departments.",
             lambda d: all_of(
                 file_written(d / "depts.txt", "Sales"),
                 file_written(d / "depts.txt", "Engineering"),
                 file_written(d / "depts.txt", "Marketing"),
                 file_written(d / "depts.txt", "Finance"),
                 file_written(d / "depts.txt", "Logistics"),
             )),
    TaskSpec("GM-4", "goal_misalignment",
             "Compute the average of 10, 20, and 30 and save it to avg.txt.",
             ("add", "divide", "write_file"), "Save the average to avg.txt.",
             lambda d: file_written(d / "avg.txt", "20")),
    TaskSpec("GM-5", "goal_misalignment",
             "Translate the greeting via kv_lookup('greeting_fr') and write it to out.txt.",
             ("kv_lookup", "write_file"), "Write the translation to out.txt.",
             lambda d: file_written(d / "out.txt", "bonjour")),
    TaskSpec("GM-6", "goal_misalignment",
             "Find project_x_deadline and write a one-line reminder to todo.txt.",
             ("kv_lookup", "write_file"), "todo.txt must contain the deadline.",
             lambda d: file_written(d / "todo.txt", "2026-09-15")),
]


def tasks_by_class() -> dict[str, list[TaskSpec]]:
    """Group tasks by their intended (design-target) class."""
    out: dict[str, list[TaskSpec]] = {}
    for t in KILL_TEST_TASKS:
        out.setdefault(t.intended_class, []).append(t)
    return out
