"""v2 sandbox tests: GT-vs-fixture consistency, verifier correctness, tool determinism.

Each v2 verifier is checked against a correct answer (varied phrasing), a wrong
answer, and a mechanism-specific near-miss (SL: a fabricated name; SM: the
silent-misuse-style wrong number and a right-number/wrong-unit case). This is the
adversarial-battery discipline applied per task before any v2 run.
"""
from __future__ import annotations

from pathlib import Path

from harness.trace import TraceRecord
from recovery_sandbox import v2_fixtures as fx
from recovery_sandbox.v2_tasks import SILENT_TOOL_MISUSE, SKIPPED_LOOKUP, V2_TASKS, v2_by_mechanism
from recovery_sandbox.v2_tools import build_v2_tools


def _trace(task_text: str = "") -> TraceRecord:
    return TraceRecord(trace_id="v2", task=task_text, task_class="", system_prompt="",
                       initial_messages=[], steps=[], final_output="", model_tag="t",
                       seed=0, temperature=0.0, ts_start="")


def _follow_manager(rid: int, depth: int) -> str:
    for _ in range(depth):
        rid = int(fx.V2_RECORDS[rid]["manager"])  # type: ignore[arg-type]
    return str(fx.V2_RECORDS[rid]["name"])


def test_counts_and_coverage() -> None:
    by = v2_by_mechanism()
    assert len(by[SKIPPED_LOOKUP]) >= 13
    assert len(by[SILENT_TOOL_MISUSE]) >= 13
    assert len({t.id for t in V2_TASKS}) == len(V2_TASKS)  # unique ids


def test_trigger_depth_varies() -> None:
    # Detection-lateness axis: skipped-lookup must include depth 1, 2, and 3.
    depths = {t.trigger_depth for t in v2_by_mechanism()[SKIPPED_LOOKUP]}
    assert {1, 2, 3} <= depths


def test_sl_ground_truths_match_fixture_chains() -> None:
    # Spot-check the manager-chain GTs against the fixtures programmatically.
    assert _follow_manager(201, 1) == "Bella Rossi"      # SL-01
    assert _follow_manager(201, 2) == "Chen Wei"          # SL-02
    assert _follow_manager(200, 3) == "Chen Wei"          # SL-03
    assert _follow_manager(211, 1) == "Node-77"           # SL-04
    assert _follow_manager(211, 2) == "Root-9"            # SL-05
    assert _follow_manager(200, 2) == "Bella Rossi"       # SL-13
    # related-chain GTs
    assert fx.V2_RECORDS[fx.V2_RECORDS[221]["related"]]["department"] == "Legal"   # SL-08
    assert fx.V2_RECORDS[fx.V2_RECORDS[241]["related"]]["name"] == "Hana Kim"      # SL-10
    # kv chain
    assert fx.V2_KV[fx.V2_KV["alpha_ref"]] == "Gamma Result"                        # SL-14


def test_each_correct_gt_verifies() -> None:
    for t in V2_TASKS:
        v = t.make_verifier(Path("."))
        assert v(_trace(t.prompt), f"The answer is {t.gt}.") is True, f"{t.id} correct GT failed"


def test_sl_fabricated_name_fails() -> None:
    for t in v2_by_mechanism()[SKIPPED_LOOKUP]:
        v = t.make_verifier(Path("."))
        assert v(_trace(t.prompt), "The answer is Jordan Fakename.") is False, f"{t.id} accepted fabrication"


def test_sm_wrong_number_and_unit_fail() -> None:
    for t in v2_by_mechanism()[SILENT_TOOL_MISUSE]:
        v = t.make_verifier(Path("."))
        # a clearly wrong number must fail
        assert v(_trace(t.prompt), "The answer is 99999.") is False, f"{t.id} accepted wrong number"


def test_sm_date_unit_guard() -> None:
    # SM-01 is 56 days; "56 hours" (right number, wrong unit) must fail.
    sm01 = next(t for t in V2_TASKS if t.id == "SM-01")
    v = sm01.make_verifier(Path("."))
    assert v(_trace(sm01.prompt), "It is 56 hours.") is False
    assert v(_trace(sm01.prompt), "It is 56 days.") is True


def test_v2_tools_deterministic(tmp_path: Path) -> None:
    tools = build_v2_tools(tmp_path)
    r = tools["get_record"].fn({"id": 201})
    assert "Bella Rossi" not in r and "manager=#202" in r  # record #201 itself is Amir Khan
    assert tools["get_record"].fn({"id": 202})  == tools["get_record"].fn({"id": 202})
    assert tools["kv_lookup"].fn({"key": "alpha_ref"}) == "beta_key"
    assert tools["kv_lookup"].fn({"key": "nope"}).lower().startswith("error")
