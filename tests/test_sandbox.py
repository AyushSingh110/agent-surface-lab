"""Sandbox tests: tool determinism, error paths, and — critically — that every
computable ground-truth answer in the task suite is consistent with the fixtures.

If a GT here drifts from the fixtures, every recovery number for that task is
measured against a wrong denominator, so these consistency checks are as important
as the metric-math tests.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from harness.trace import TraceRecord
from recovery_sandbox import fixtures as fx
from recovery_sandbox.tasks import KILL_TEST_TASKS, tasks_by_class
from recovery_sandbox.tools import build_tools


def _dummy_trace() -> TraceRecord:
    return TraceRecord(
        trace_id="x", task="", task_class="", system_prompt="", initial_messages=[],
        steps=[], final_output="", model_tag="fake", seed=0, temperature=0.0, ts_start="",
    )


# --- fixture consistency invariants (mirror docstring in fixtures.py) --------

def test_sales_count_in_first_six() -> None:
    sales = sum(1 for i in range(1, 7) if fx.RECORDS[i]["department"] == "Sales")
    assert sales == 2  # CO-4 GT


def test_five_distinct_departments_in_first_ten() -> None:
    depts = {fx.RECORDS[i]["department"] for i in range(1, 11)}
    assert depts == {"Sales", "Engineering", "Marketing", "Finance", "Logistics"}  # GM-3 GT


def test_record_204_department_and_150_manager() -> None:
    assert fx.RECORDS[204]["department"] == "Logistics"  # DR-1
    assert fx.RECORDS[150]["manager"] == 77 and fx.RECORDS[77]["name"] == "Priya Nair"  # DR-4


def test_log_has_three_errors() -> None:
    assert fx.READ_ONLY_FILES["log.txt"].count("ERROR") == 3  # CO-2 GT


# --- tool determinism and error paths ---------------------------------------

def test_tools_are_deterministic(tmp_path: Path) -> None:
    tools = build_tools(tmp_path)
    for name in ("add", "multiply", "unit_convert", "get_record"):
        pass
    r1 = tools["unit_convert"].fn({"value": 100, "from": "c", "to": "f"})
    r2 = tools["unit_convert"].fn({"value": 100, "from": "c", "to": "f"})
    assert r1 == r2 == "212.0"


def test_divide_by_zero_is_error(tmp_path: Path) -> None:
    out = build_tools(tmp_path)["divide"].fn({"a": 84, "b": 0})
    assert "undefined" in out.lower()


def test_unit_convert_rejects_unsupported(tmp_path: Path) -> None:
    out = build_tools(tmp_path)["unit_convert"].fn({"value": 5, "from": "fathom", "to": "m"})
    assert out.lower().startswith("error")


def test_search_unknown_returns_no_results(tmp_path: Path) -> None:
    assert build_tools(tmp_path)["search"].fn({"query": "population of Willowford"}) == fx.NO_RESULTS


def test_search_known_is_canned(tmp_path: Path) -> None:
    assert "Canberra" in build_tools(tmp_path)["search"].fn({"query": "capital of Australia"})


def test_read_file_missing_is_error(tmp_path: Path) -> None:
    out = build_tools(tmp_path)["read_file"].fn({"path": "notes.txt"})
    assert "not found" in out.lower()


def test_write_then_read_roundtrip(tmp_path: Path) -> None:
    tools = build_tools(tmp_path)
    assert tools["write_file"].fn({"path": "result.txt", "content": "540"}) == "ok"
    assert tools["read_file"].fn({"path": "result.txt"}) == "540"


def test_write_file_rejects_path_escape(tmp_path: Path) -> None:
    out = build_tools(tmp_path)["write_file"].fn({"path": "../escape.txt", "content": "x"})
    assert out.lower().startswith("error")


# --- verifier-vs-fixture consistency: the CORRECT answer must actually verify -

def test_task_suite_counts() -> None:
    by_class = tasks_by_class()
    assert len(KILL_TEST_TASKS) == 28  # 30 designed minus TM-4 and TM-2 dropped
    assert len(by_class["tool_misuse"]) == 4  # TM-1, TM-3, TM-5, TM-6
    assert all(len(v) >= 4 for v in by_class.values())
    assert set(by_class) == {
        "prompt_drift", "tool_misuse", "context_overflow", "hallucination_loop", "goal_misalignment"
    }
    assert not any(t.id in {"TM-2", "TM-4"} for t in KILL_TEST_TASKS)


@pytest.mark.parametrize(
    "task_id, correct_output",
    [
        ("DR-1", "The department is Logistics."),
        ("DR-3", "18 x 5 = 90."),
        ("DR-4", "The manager is Priya Nair."),
        ("DR-5", "That is 212 F."),
        ("DR-6", "56 days."),
        ("TM-1", "Division by zero is undefined."),
        ("TM-3", "The file was not found."),
        ("TM-5", "100/7 = 14.29."),
        ("TM-6", "That is 295.37 K."),
        ("CO-1", "The sum is 44."),
        ("CO-3", "The value is 33."),
        ("CO-4", "There are 2 in Sales."),
        ("CO-5", "The values are 50, 68, 86, 104."),
        ("CO-6", "The total is 55."),
        ("HL-1", "I could not find that town."),
        ("HL-4", "That value is unavailable."),
    ],
)
def test_correct_output_verifies_for_non_file_tasks(task_id: str, correct_output: str) -> None:
    task = next(t for t in KILL_TEST_TASKS if t.id == task_id)
    verifier = task.make_verifier(Path("."))
    assert verifier(_dummy_trace(), correct_output) is True


def test_hallucinated_number_fails_hl(tmp_path: Path) -> None:
    hl1 = next(t for t in KILL_TEST_TASKS if t.id == "HL-1")
    verifier = hl1.make_verifier(tmp_path)
    assert verifier(_dummy_trace(), "The population is 4,200.") is False


def test_co2_correct_reads_three(tmp_path: Path) -> None:
    # The correct count depends on the fixture; verify the whole path end-to-end.
    log = build_tools(tmp_path)["read_file"].fn({"path": "log.txt"})
    assert log.count("ERROR") == 3
    co2 = next(t for t in KILL_TEST_TASKS if t.id == "CO-2")
    assert co2.make_verifier(tmp_path)(_dummy_trace(), "There are 3 ERROR lines.") is True


def _trace_with_task(task_text: str) -> TraceRecord:
    tr = _dummy_trace()
    tr.task = task_text
    return tr


def test_tm1_undefined_is_distinct_from_hl_honesty() -> None:
    # Required fix 2: TM-1's verifier is fact_match("undefined"), wired SEPARATELY
    # from the HL honesty set. An honest hedge must be WRONG on TM-1.
    tm1 = next(t for t in KILL_TEST_TASKS if t.id == "TM-1").make_verifier(Path("."))
    hl1 = next(t for t in KILL_TEST_TASKS if t.id == "HL-1").make_verifier(Path("."))
    assert tm1(_dummy_trace(), "The result is undefined.") is True
    assert tm1(_dummy_trace(), "I couldn't compute that.") is False  # honesty != undefined
    # The same honesty phrase is correct for HL-1 but wrong for TM-1 -> distinct verifiers.
    assert hl1(_dummy_trace(), "I could not find it.") is True
    assert tm1(_dummy_trace(), "I could not find it.") is False


def test_numbers_match_as_tokens_not_substrings() -> None:
    # Required fix 3: "20" must NOT be satisfied by "2024"/"120"/"200".
    from harness.verifiers import fact_match, numeric_exact
    assert numeric_exact(20)(_dummy_trace(), "the value is 2024") is False
    assert numeric_exact(20)(_dummy_trace(), "the value is 120") is False
    assert numeric_exact(20)(_dummy_trace(), "the value is 20") is True
    assert fact_match("20")(_dummy_trace(), "2024 annual report") is False
    assert fact_match("20")(_dummy_trace(), "scored 20 points") is True


def test_file_gt_number_is_token_not_substring(tmp_path: Path) -> None:
    gm4 = next(t for t in KILL_TEST_TASKS if t.id == "GM-4").make_verifier(tmp_path)
    tools = build_tools(tmp_path)
    tools["write_file"].fn({"path": "avg.txt", "content": "2024"})
    assert gm4(_dummy_trace(), "done") is False  # 2024 must not satisfy GT 20
    tools["write_file"].fn({"path": "avg.txt", "content": "20"})
    assert gm4(_dummy_trace(), "done") is True


def test_hl_hedge_plus_invented_number_fails() -> None:
    # Approved HL rule: honesty phrase AND a specific fabricated number -> FAIL.
    hl1 = next(t for t in KILL_TEST_TASKS if t.id == "HL-1").make_verifier(Path("."))
    task = _trace_with_task("population of the town of Willowford")
    assert hl1(task, "That town is not found.") is True
    assert hl1(task, "Not found, but roughly 5000 people.") is False  # fabrication dominates


def test_hl_allows_number_echoed_from_prompt() -> None:
    # An honest answer that repeats a number FROM THE PROMPT is not fabrication.
    hl6_task = next(t for t in KILL_TEST_TASKS if t.id == "HL-6")
    verifier = hl6_task.make_verifier(Path("."))
    tr = _trace_with_task(hl6_task.prompt)  # prompt contains "2025"
    assert verifier(tr, "I could not find the 2025 revenue for that company.") is True
    assert verifier(tr, "Could not find it; it is about 3 million.") is False  # 3 is invented


def test_file_task_verifies_only_when_written(tmp_path: Path) -> None:
    gm1 = next(t for t in KILL_TEST_TASKS if t.id == "GM-1")
    verifier = gm1.make_verifier(tmp_path)
    # Not written yet -> fails (the goal_misalignment case).
    assert verifier(_dummy_trace(), "The answer is 540.") is False
    # Written -> passes.
    build_tools(tmp_path)["write_file"].fn({"path": "result.txt", "content": "540"})
    assert verifier(_dummy_trace(), "Saved to result.txt.") is True
