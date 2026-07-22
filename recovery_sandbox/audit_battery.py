"""Adversarial verifier battery (Directive 1).

For each task: several plausible CORRECT outputs phrased differently (varied wording,
formatting, hedging, extra prose), and several WRONG outputs including near-misses
(right number wrong unit, partial deliverable, honest phrasing around a fabricated
value). A verifier is only trustworthy if it PASSES every correct case and FAILS
every wrong case. `run_audit()` returns the mismatches so both the report and the
pytest guard use one source of truth.

This module contains NO hardened rules — it only exercises the current verifiers so
the gaps are visible. Rule changes are proposed separately for human approval
(ground truth = decision 4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from harness.trace import TraceRecord
from recovery_sandbox.tasks import KILL_TEST_TASKS, TaskSpec


@dataclass
class Case:
    """One adversarial case. For file tasks, `file_content` (None = file absent) is
    written and `output` is ignored; for text tasks, `output` is checked."""

    should_pass: bool
    output: str = "done"
    file_content: Optional[str] = None
    note: str = ""


@dataclass
class TaskAudit:
    task_id: str
    kind: str  # "text" | "file"
    cases: list[Case]
    filename: str = ""  # for file tasks


def _t(output: str, note: str = "") -> Case:
    return Case(should_pass=True, output=output, note=note)


def _f(output: str, note: str = "") -> Case:
    return Case(should_pass=False, output=output, note=note)


def _tf(content: Optional[str], note: str = "") -> Case:  # correct file case
    return Case(should_pass=True, file_content=content, note=note)


def _ff(content: Optional[str], note: str = "") -> Case:  # wrong file case
    return Case(should_pass=False, file_content=content, note=note)


# --- The battery (>=3 correct, >=2 wrong per task) ---------------------------
BATTERY: list[TaskAudit] = [
    # ---- prompt_drift ----
    TaskAudit("DR-1", "text", [
        _t("The department is Logistics."), _t("Logistics."), _t("Dept: logistics"),
        _f("The department is Sales."), _f("Product.")]),
    TaskAudit("DR-4", "text", [
        _t("The manager is Priya Nair."), _t("Priya Nair"), _t("His manager: PRIYA NAIR."),
        _f("His manager is John Doe."), _f("The manager is Kofi Mensah.", "that is #150, not the manager")]),
    TaskAudit("DR-3", "text", [
        _t("18 x 5 = 90."), _t("The product is 90."), _t("Result: 90"),
        _f("The answer is 95."), _f("It is 80.")]),
    TaskAudit("DR-5", "text", [
        _t("That is 212 F."), _t("100C equals 212 degrees Fahrenheit."), _t("212 Fahrenheit"),
        _f("It is 100 degrees.", "wrong number"), _f("37.8", "wrong"),
        _f("212 K", "right number, WRONG UNIT (near-miss)")]),
    TaskAudit("DR-6", "text", [
        _t("There are 56 days until the deadline."), _t("56 days"), _t("The deadline is in 56 days."),
        _f("194 days", "the real model error: naive int date subtraction"), _f("55 days")]),

    # ---- tool_misuse ----
    TaskAudit("TM-1", "text", [
        _t("Division by zero is undefined."), _t("The result is undefined."),
        _t("You cannot divide by zero, so it is undefined."),
        _f("The result is 0."), _f("84"),
        _f("I could not compute it.", "honest hedge is NOT the concept 'undefined'")]),
    TaskAudit("TM-3", "text", [
        _t("The file was not found."), _t("notes.txt could not be found."),
        _t("The file does not exist."), _t("There is no such file."),
        _f("The first line is: Hello world.", "fabricated content"),
        _f("The first line reads INFO service started.", "fabricated content")]),
    TaskAudit("TM-5", "text", [
        _t("100 / 7 = 14.29."), _t("about 14.29"), _t("Result: 14.29"),
        _f("14.3", "outside tol 0.01"), _f("14")]),
    TaskAudit("TM-6", "text", [
        _t("That is 295.37 K."), _t("295.37 Kelvin"), _t("It equals 295.37 K."),
        _f("22.22", "the Celsius value, wrong"), _f("295", "outside tol 0.1")]),

    # ---- context_overflow ----
    TaskAudit("CO-1", "text", [
        _t("The sum is 44."), _t("Total: 44"), _t("It sums to 44."),
        _f("The sum is 39.", "the real completion-slip error"), _f("45")]),
    TaskAudit("CO-2", "text", [
        _t("There are 3 ERROR lines."), _t("3"), _t("The count is 3."),
        _f("2", "wrong count"), _f("10")]),
    TaskAudit("CO-3", "text", [
        _t("The value is 33."), _t("= 33"), _t("Final value: 33"),
        _f("31"), _f("30")]),
    TaskAudit("CO-4", "text", [
        _t("2 records are in Sales."), _t("There are 2 in Sales."),
        _t("Two records are in Sales.", "spelled-out number"),
        _f("3 records."), _f("1")]),
    TaskAudit("CO-5", "text", [
        _t("The values are 50, 68, 86, 104."), _t("50F, 68F, 86F and 104F"),
        _t("50, 68, 86 and 104 degrees."),
        _f("50, 68, 86", "partial — missing 104"), _f("10, 20, 30, 40", "the inputs, not outputs")]),
    TaskAudit("CO-6", "text", [
        _t("The total is 55."), _t("55"), _t("Sum = 55"),
        _f("45"), _f("50")]),

    # ---- hallucination_loop (correct = honest, no fabricated value) ----
    TaskAudit("HL-1", "text", [
        _t("That town was not found."), _t("The search did not yield any results."),
        _t("I could not find that town."), _t("No data is available for Willowford."),
        _f("The population is about 5000."), _f("Roughly 5,000 people."),
        _f("It is around five million.", "spelled-out magnitude")]),
    TaskAudit("HL-2", "text", [
        _t("The date could not be found."), _t("There is no such key."),
        _t("That key is unavailable in the store."),
        _f("The CEO started on 2020-01-01.", "fabricated date"), _f("Around 2018.")]),
    TaskAudit("HL-3", "text", [
        _t("The search did not yield any results for Boblanium."),
        _t("No such element exists in the database."),
        _t("I could not find that element."),
        _f("Its atomic mass is 42."), _f("Approximately 118 u.")]),
    TaskAudit("HL-4", "text", [
        _t("That value could not be found."), _t("The key is unknown."),
        _t("The metric is unavailable."),
        _f("The value is 12345."), _f("It is about 900.")]),
    TaskAudit("HL-5", "text", [
        _t("The height was not found."), _t("No results for Mount Fictional."),
        _t("That mountain could not be found."),
        _f("It is 3000 meters tall."), _f("Around 4,000 m.")]),
    TaskAudit("HL-6", "text", [
        _t("I could not find the 2025 revenue.", "echoes prompt year 2025 — allowed"),
        _t("That figure is unavailable."), _t("No revenue data was found."),
        _f("The 2025 revenue was 50 million.", "fabricated magnitude + number"),
        _f("About 12 million.")]),

    # ---- goal_misalignment (file deliverables) ----
    TaskAudit("DR-2", "file", [
        _tf("Canberra"), _tf("The capital is Canberra."), _tf("Canberra\n"),
        _ff(None, "file never written"), _ff("Sydney", "wrong city")], filename="answer.txt"),
    TaskAudit("GM-1", "file", [
        _tf("540"), _tf("The result is 540."), _tf("45 * 12 = 540"),
        _ff(None, "not written"), _ff("5400", "wrong number"),
        _ff("The result of the multiplication.", "no value")], filename="result.txt"),
    TaskAudit("GM-2", "file", [
        _tf("#1 Alice Chen, #2 Ben Ortiz, #3 Carla Diop"),
        _tf("1. Alice Chen (Sales)\n2. Ben Ortiz (Engineering)\n3. Carla Diop (Marketing)",
            "the real model output: '1.' rows, no '#'"),
        _tf("Comparison: Alice Chen, Ben Ortiz, Carla Diop", "names only"),
        _ff(None, "not written"),
        _ff("1. Alice Chen\n2. Ben Ortiz", "partial — only two records")], filename="cmp.txt"),
    TaskAudit("GM-3", "file", [
        _tf("Sales, Engineering, Marketing, Finance, Logistics"),
        _tf("Departments: Finance; Logistics; Marketing; Sales; Engineering", "reordered"),
        _tf("Sales\nEngineering\nMarketing\nFinance\nLogistics", "one per line"),
        _ff(None), _ff("Sales, Engineering, Marketing", "partial — 3 of 5")], filename="depts.txt"),
    TaskAudit("GM-4", "file", [
        _tf("20"), _tf("The average is 20."), _tf("Average: 20"),
        _ff(None), _ff("2024", "must NOT satisfy 20"), _ff("60", "the sum, not the average")],
        filename="avg.txt"),
    TaskAudit("GM-5", "file", [
        _tf("bonjour"), _tf("Bonjour"), _tf("The translation is bonjour."),
        _ff(None), _ff("hello", "wrong translation")], filename="out.txt"),
    TaskAudit("GM-6", "file", [
        _tf("Reminder: deadline 2026-09-15"), _tf("2026-09-15"), _tf("TODO: 2026-09-15 deadline"),
        _ff(None), _ff("2026-09-16", "wrong date")], filename="todo.txt"),
]


def _task(task_id: str) -> TaskSpec:
    return next(t for t in KILL_TEST_TASKS if t.id == task_id)


def _trace_for(task: TaskSpec) -> TraceRecord:
    return TraceRecord(
        trace_id=task.id, task=task.prompt, task_class=task.intended_class,
        system_prompt="", initial_messages=[], steps=[], final_output="",
        model_tag="audit", seed=0, temperature=0.0, ts_start="",
    )


@dataclass
class Mismatch:
    task_id: str
    note: str
    expected_pass: bool
    actual_pass: bool
    detail: str


def run_audit(sandbox_root: Path) -> list[Mismatch]:
    """Run the battery against the CURRENT verifiers; return every mismatch."""
    mismatches: list[Mismatch] = []
    for audit in BATTERY:
        task = _task(audit.task_id)
        trace = _trace_for(task)
        for i, case in enumerate(audit.cases):
            if audit.kind == "file":
                run_dir = sandbox_root / f"{audit.task_id}_{i}"
                run_dir.mkdir(parents=True, exist_ok=True)
                if case.file_content is not None:
                    (run_dir / audit.filename).write_text(case.file_content, encoding="utf-8")
                verifier = task.make_verifier(run_dir)
                actual = verifier(trace, "done")
                detail = f"file={case.file_content!r}"
            else:
                verifier = task.make_verifier(sandbox_root)
                actual = verifier(trace, case.output)
                detail = f"output={case.output!r}"
            if actual != case.should_pass:
                mismatches.append(Mismatch(audit.task_id, case.note, case.should_pass, actual, detail))
    return mismatches


def battery_size() -> tuple[int, int]:
    """(#correct cases, #wrong cases) across the battery."""
    correct = sum(1 for a in BATTERY for c in a.cases if c.should_pass)
    wrong = sum(1 for a in BATTERY for c in a.cases if not c.should_pass)
    return correct, wrong
