"""Metric-math tests — a wrong metric silently invalidates the paper.

Every number below is hand-computed in the comments so the assertion is checkable
by eye, independent of the implementation.
"""
from __future__ import annotations

import pytest

from harness.metrics import (
    ReplayOutcome,
    is_near_boundary,
    iatrogenic_rate,
    mean_recovery,
    net_improvement,
    recovery_matrix,
)


def _o(tid: str, intervention: str, successes: int, n: int, cls: str = "hallucination_loop") -> ReplayOutcome:
    return ReplayOutcome(trace_id=tid, failure_class=cls, intervention=intervention, successes=successes, n=n)


def test_outcome_validation() -> None:
    with pytest.raises(ValueError):
        _o("a", "no_op", successes=3, n=2)  # successes > n
    with pytest.raises(ValueError):
        _o("a", "no_op", successes=0, n=0)  # n < 1


def test_rate() -> None:
    assert _o("a", "no_op", 1, 2).rate == 0.5
    assert _o("a", "no_op", 3, 3).rate == 1.0


def test_mean_recovery_is_macro() -> None:
    # rates 1.0, 0.0, 0.5 -> mean 0.5 (each trace weighted equally regardless of n).
    outs = [_o("a", "no_op", 2, 2), _o("b", "no_op", 0, 4), _o("c", "no_op", 1, 2)]
    assert mean_recovery(outs) == pytest.approx(0.5)


def test_mean_recovery_empty_raises() -> None:
    with pytest.raises(ValueError):
        mean_recovery([])


def _paired_sets() -> tuple[list[ReplayOutcome], list[ReplayOutcome]]:
    # no_op:   A 2/2=1.0, B 0/2=0.0, C 1/2=0.5
    # reflect: A 1/2=0.5 (<1.0 harmed), B 0/2=0.0 (tie, not harmed), C 0/2=0.0 (<0.5 harmed)
    noop = [_o("A", "no_op", 2, 2), _o("B", "no_op", 0, 2), _o("C", "no_op", 1, 2)]
    reflect = [_o("A", "reflect", 1, 2), _o("B", "reflect", 0, 2), _o("C", "reflect", 0, 2)]
    return reflect, noop


def test_iatrogenic_rate() -> None:
    reflect, noop = _paired_sets()
    # harmed on A and C, tie on B -> 2/3.
    assert iatrogenic_rate(reflect, noop) == pytest.approx(2 / 3)


def test_net_improvement() -> None:
    reflect, noop = _paired_sets()
    # (0.5-1.0) + (0.0-0.0) + (0.0-0.5) = -1.0 ; /3 -> -1/3.
    assert net_improvement(reflect, noop) == pytest.approx(-1 / 3)


def test_pairing_mismatch_raises() -> None:
    reflect = [_o("A", "reflect", 1, 2)]
    noop = [_o("B", "no_op", 1, 2)]
    with pytest.raises(ValueError):
        iatrogenic_rate(reflect, noop)


def test_duplicate_trace_raises() -> None:
    dup = [_o("A", "reflect", 1, 2), _o("A", "reflect", 0, 2)]
    noop = [_o("A", "no_op", 1, 2)]
    with pytest.raises(ValueError):
        iatrogenic_rate(dup, noop)


def test_is_near_boundary() -> None:
    # p=0.5, n=2: SE=sqrt(.25/2)=0.354; |0.5-0.5|=0 < 0.354 -> near.
    assert is_near_boundary(_o("a", "x", 1, 2)) is True
    # p=1.0: SE=0; |1-0.5|=0.5 < 0 is False -> not near (a certain cell).
    assert is_near_boundary(_o("a", "x", 2, 2)) is False
    assert is_near_boundary(_o("a", "x", 0, 2)) is False


def test_recovery_matrix_groups_by_cell() -> None:
    outs = [
        _o("A", "no_op", 2, 2, cls="tool_misuse"),
        _o("B", "no_op", 0, 2, cls="tool_misuse"),
        _o("A", "reflect", 1, 2, cls="tool_misuse"),
        _o("A", "no_op", 1, 2, cls="goal_misalignment"),
    ]
    mat = recovery_matrix(outs)
    assert mat[("no_op", "tool_misuse")] == pytest.approx(0.5)  # (1.0 + 0.0)/2
    assert mat[("reflect", "tool_misuse")] == pytest.approx(0.5)
    assert mat[("no_op", "goal_misalignment")] == pytest.approx(0.5)
    assert len(mat) == 3


def test_recovery_matrix_empty() -> None:
    assert recovery_matrix([]) == {}
