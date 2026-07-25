"""Replay/reconstruct tests — the correctness of counterfactual replay hinges here.

The key guarantee (design lesson from the DoVer read): `reconstruct(trace, k)` must
reproduce the EXACT context the model saw entering step k. If it doesn't, every
recovery number is measured against the wrong prompt.
"""
from __future__ import annotations

import pytest

from harness.backend import ChatResponse, FakeBackend
from harness.config import Config
from harness.interventions import no_op, reflect_and_retry, requirement_injection, rollback_n
from harness.replay import reconstruct, replay_cell
from harness.tools import ARITHMETIC_TOOLS, ToolRegistry
from harness.trace import TraceRecord
from harness.verifiers import numeric_exact


def test_reconstruct_matches_recorded_snapshots(recorded_trace: TraceRecord) -> None:
    # For every step, the rebuilt context must equal the exact recorded snapshot.
    for k, step in enumerate(recorded_trace.steps):
        assert reconstruct(recorded_trace, k) == step.context_snapshot, f"mismatch at k={k}"


def test_reconstruct_zero_is_initial(recorded_trace: TraceRecord) -> None:
    assert reconstruct(recorded_trace, 0) == recorded_trace.initial_messages


def test_reconstruct_matches_what_model_actually_saw(recorded_trace: TraceRecord) -> None:
    # Cross-check against the FakeBackend's independently-captured contexts.
    seen = recorded_trace._seen_contexts  # type: ignore[attr-defined]
    for k in range(len(recorded_trace.steps)):
        assert reconstruct(recorded_trace, k) == seen[k], f"reconstruct != seen at k={k}"


def test_reconstruct_out_of_range_raises(recorded_trace: TraceRecord) -> None:
    with pytest.raises(IndexError):
        reconstruct(recorded_trace, len(recorded_trace.steps) + 1)
    with pytest.raises(IndexError):
        reconstruct(recorded_trace, -1)


def test_reconstruct_full_length_ok(recorded_trace: TraceRecord) -> None:
    # k == number of steps is valid (context after the last step); must not raise.
    msgs = reconstruct(recorded_trace, len(recorded_trace.steps))
    assert msgs[0]["role"] == "system"


def _const_backend(final_text: str, n_calls: int) -> FakeBackend:
    """A FakeBackend that answers `final_text` immediately, enough times for n replays."""
    return FakeBackend([ChatResponse(content=final_text, tool_name=None, tool_args=None)] * n_calls)


def test_replay_cell_returns_distribution_not_single(recorded_trace: TraceRecord) -> None:
    # no_op resumes from k and (per the fake) immediately answers "35" three times.
    registry = ToolRegistry(list(ARITHMETIC_TOOLS))
    config = Config(temperature=0.7, n_replays=3, max_turns=8)
    backend = _const_backend("The result is 35.", n_calls=3)
    successes = replay_cell(
        trace=recorded_trace,
        k=1,
        intervention=no_op,
        tools=registry,
        backend=backend,
        config=config,
        verifier=numeric_exact(35),
    )
    assert successes == [True, True, True]  # a length-N distribution, here all recovered


def test_replay_cell_counts_failures(recorded_trace: TraceRecord) -> None:
    registry = ToolRegistry(list(ARITHMETIC_TOOLS))
    config = Config(n_replays=2, max_turns=8)
    backend = _const_backend("The result is 999.", n_calls=2)  # wrong answer
    successes = replay_cell(
        trace=recorded_trace,
        k=1,
        intervention=no_op,
        tools=registry,
        backend=backend,
        config=config,
        verifier=numeric_exact(35),
    )
    assert successes == [False, False]


def test_rollback_underflow_reports_restart_clean(recorded_trace: TraceRecord) -> None:
    # k=1 < n=2: no silent clamp — the outcome must self-report as restart_clean.
    outcome = rollback_n(2)(recorded_trace, 1, Config())
    assert outcome.resume_turn == 0
    assert outcome.resume_messages == recorded_trace.initial_messages
    assert outcome.name == "restart_clean"  # NOT "rollback_2"


def test_rollback_genuine_rewind_keeps_name(recorded_trace: TraceRecord) -> None:
    # A 3-step trace at k=2 with n=2 is a real rewind to step 0, still named rollback_2.
    # (recorded_trace has 3 steps; use k=2 so k-n=0 >= 0.)
    outcome = rollback_n(2)(recorded_trace, 2, Config())
    assert outcome.resume_turn == 0
    assert outcome.name == "rollback_2"


def test_reflect_injects_prompt_without_changing_prefix(recorded_trace: TraceRecord) -> None:
    outcome = reflect_and_retry(recorded_trace, 1, Config())
    base = reconstruct(recorded_trace, 1)
    assert outcome.resume_messages[: len(base)] == base
    assert outcome.resume_messages[-1]["role"] == "user"
    assert outcome.resume_turn == 1


def test_requirement_injection_requires_a_requirement(recorded_trace: TraceRecord) -> None:
    recorded_trace.requirement = None
    with pytest.raises(ValueError):
        requirement_injection(recorded_trace, 1, Config())
