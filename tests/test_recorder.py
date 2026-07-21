"""Recorder tests: JSONL round-trip must preserve a trace and its steps exactly."""
from __future__ import annotations

from pathlib import Path

import pytest

from harness.recorder import append_trace, load_traces
from harness.trace import TraceRecord


def test_trace_jsonl_roundtrip(recorded_trace: TraceRecord) -> None:
    # asdict-based serialization must survive a write/read unchanged.
    line = recorded_trace.to_json_line()
    back = TraceRecord.from_json_line(line)
    assert back.trace_id == recorded_trace.trace_id
    assert back.final_output == recorded_trace.final_output
    assert len(back.steps) == len(recorded_trace.steps)
    for a, b in zip(recorded_trace.steps, back.steps):
        assert a.turn == b.turn
        assert a.context_snapshot == b.context_snapshot
        assert a.tool_name == b.tool_name
        assert a.tool_args == b.tool_args
        assert a.tool_result == b.tool_result


def test_append_and_load(tmp_path: Path, recorded_trace: TraceRecord) -> None:
    fp = tmp_path / "traces.jsonl"
    append_trace(recorded_trace, fp)
    append_trace(recorded_trace, fp)
    loaded = load_traces(fp)
    assert len(loaded) == 2
    assert loaded[0].task_class == "arithmetic"


def test_ground_truth_fields_default_none(recorded_trace: TraceRecord) -> None:
    # A freshly recorded trace must not carry fabricated labels (CLAUDE.md §3).
    assert recorded_trace.answer_correct is None
    assert recorded_trace.failure_class is None
    assert recorded_trace.failure_step_k is None


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_traces(tmp_path / "nope.jsonl")
