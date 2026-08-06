"""Tests for the bootstrap CI module.

A wrong interval is as damaging as a wrong point estimate -- it would let a claim
be published as statistically supported when it is not -- so the properties that
the headline tables depend on are pinned here explicitly.
"""
from __future__ import annotations

import pytest

from harness.bootstrap import (
    Interval,
    mean_ci,
    paired_diff_ci,
    rule_of_three_upper,
    _percentile,
)
from harness.metrics import ReplayOutcome, mean_recovery

FAST = 400  # iterations for tests where the exact bound does not matter


def _cell(rates: dict[str, float], n: int = 10) -> dict[str, list[bool]]:
    """Build a cell whose traces have the given per-trace success rates."""
    return {tid: [i < round(r * n) for i in range(n)] for tid, r in rates.items()}


class TestPercentile:
    def test_interpolates_between_values(self) -> None:
        assert _percentile([0.0, 1.0], 0.5) == pytest.approx(0.5)

    def test_endpoints(self) -> None:
        values = [1.0, 2.0, 3.0, 4.0]
        assert _percentile(values, 0.0) == 1.0
        assert _percentile(values, 1.0) == 4.0

    def test_single_value(self) -> None:
        assert _percentile([7.0], 0.5) == 7.0

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            _percentile([], 0.5)


class TestRuleOfThree:
    def test_uses_trace_count_not_replay_count(self) -> None:
        # 13 traces x 10 replays, all zero: the bound must be 3/13, NOT 3/130.
        # Using the replay count would claim ~10x more precision than a clustered
        # design supports, which is the whole point of the cluster-level choice.
        assert rule_of_three_upper(13) == pytest.approx(3 / 13)

    def test_capped_at_one(self) -> None:
        assert rule_of_three_upper(2) == 1.0

    def test_rejects_zero(self) -> None:
        with pytest.raises(ValueError):
            rule_of_three_upper(0)


class TestMeanCI:
    def test_point_matches_metrics_macro_mean(self) -> None:
        """The CI's point estimate must equal the published macro mean exactly.

        If these ever diverge, the tables and their intervals describe different
        quantities.
        """
        cell = _cell({"t1": 0.2, "t2": 0.8, "t3": 0.5})
        outcomes = [
            ReplayOutcome(tid, "skipped_lookup", "arm", sum(d), len(d))
            for tid, d in cell.items()
        ]
        assert mean_ci(cell, iterations=FAST).point == pytest.approx(mean_recovery(outcomes))

    def test_deterministic_under_same_seed(self) -> None:
        cell = _cell({"t1": 0.3, "t2": 0.7, "t3": 0.1, "t4": 0.9})
        a = mean_ci(cell, iterations=FAST, seed=123)
        b = mean_ci(cell, iterations=FAST, seed=123)
        assert (a.low, a.high, a.point) == (b.low, b.high, b.point)

    def test_different_seeds_give_similar_but_not_identical_bounds(self) -> None:
        cell = _cell({"t1": 0.3, "t2": 0.7, "t3": 0.1, "t4": 0.9})
        a = mean_ci(cell, iterations=2000, seed=1)
        b = mean_ci(cell, iterations=2000, seed=2)
        assert a.low != b.low or a.high != b.high
        assert a.low == pytest.approx(b.low, abs=0.15)

    def test_interval_brackets_the_point(self) -> None:
        cell = _cell({"t1": 0.2, "t2": 0.6, "t3": 0.4, "t4": 0.8, "t5": 0.5})
        ci = mean_ci(cell, iterations=2000)
        assert ci.low <= ci.point <= ci.high

    def test_all_zero_cell_is_degenerate_with_conservative_bound(self) -> None:
        """The surface-form 'unrecoverable' cells look like this.

        Reporting a bare [0.00, 0.00] would assert certainty we do not have, so the
        cell must be flagged and carry the rule-of-three bound instead.
        """
        cell = _cell({f"t{i}": 0.0 for i in range(13)})
        ci = mean_ci(cell, iterations=FAST)
        assert ci.point == 0.0
        assert ci.degenerate
        assert ci.conservative_upper == pytest.approx(3 / 13)
        assert "<=" in ci.format()

    def test_all_one_cell_is_degenerate_without_upper_bound(self) -> None:
        cell = _cell({f"t{i}": 1.0 for i in range(8)})
        ci = mean_ci(cell, iterations=FAST)
        assert ci.point == 1.0
        assert ci.degenerate
        assert ci.conservative_upper is None

    def test_fewer_traces_gives_a_wider_interval(self) -> None:
        """The between-trace level must dominate -- this is why the bootstrap is
        two-level. Depth-3 cells (n=6) must visibly carry more uncertainty than
        depth-1 cells (n=21) at the same point estimate."""
        spread = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        small = _cell({f"t{i}": r for i, r in enumerate(spread)})
        large = _cell({f"t{i}": spread[i % len(spread)] for i in range(24)})
        small_ci = mean_ci(small, iterations=3000)
        large_ci = mean_ci(large, iterations=3000)
        assert small_ci.point == pytest.approx(large_ci.point, abs=0.02)
        assert (small_ci.high - small_ci.low) > (large_ci.high - large_ci.low)

    def test_heterogeneous_traces_widen_the_interval(self) -> None:
        """Two cells with the SAME macro mean but different between-trace spread
        must not get the same interval; a replay-only bootstrap would give them
        near-identical widths."""
        homogeneous = _cell({f"t{i}": 0.5 for i in range(8)})
        heterogeneous = _cell({f"t{i}": (1.0 if i % 2 else 0.0) for i in range(8)})
        hom = mean_ci(homogeneous, iterations=3000)
        het = mean_ci(heterogeneous, iterations=3000)
        assert hom.point == pytest.approx(het.point, abs=0.01)
        assert (het.high - het.low) > (hom.high - hom.low)

    def test_empty_cell_raises(self) -> None:
        with pytest.raises(ValueError, match="no traces"):
            mean_ci({})

    def test_trace_with_no_replays_raises(self) -> None:
        with pytest.raises(ValueError, match="no replays"):
            mean_ci({"t1": []})


class TestPairedDiffCI:
    def test_separated_arms_exclude_zero(self) -> None:
        """The headline contrast shape: lookup_permitting ~1.0 vs neutral ~0.16."""
        high = _cell({f"t{i}": 1.0 for i in range(10)})
        low = _cell({f"t{i}": 0.1 for i in range(10)})
        ci = paired_diff_ci(high, low, iterations=3000)
        assert ci.point == pytest.approx(0.9, abs=0.05)
        assert ci.excludes_zero
        assert ci.low > 0

    def test_identical_arms_give_a_zero_difference(self) -> None:
        cell = _cell({f"t{i}": 0.5 for i in range(10)})
        ci = paired_diff_ci(cell, dict(cell), iterations=2000)
        assert ci.point == pytest.approx(0.0, abs=1e-9)
        assert ci.low <= 0.0 <= ci.high

    def test_overlapping_arms_do_not_exclude_zero(self) -> None:
        a = _cell({f"t{i}": (0.5 if i % 2 else 0.6) for i in range(8)})
        b = _cell({f"t{i}": (0.6 if i % 2 else 0.5) for i in range(8)})
        assert not paired_diff_ci(a, b, iterations=3000).excludes_zero

    def test_mismatched_trace_sets_raise(self) -> None:
        """Guards the same failure `metrics._pair` guards: an unpaired comparison
        would silently compare different populations."""
        a = _cell({"t1": 0.5, "t2": 0.5})
        b = _cell({"t1": 0.5, "t3": 0.5})
        with pytest.raises(ValueError, match="identical trace sets"):
            paired_diff_ci(a, b)

    def test_deterministic_under_same_seed(self) -> None:
        a = _cell({f"t{i}": 0.8 for i in range(6)})
        b = _cell({f"t{i}": 0.2 for i in range(6)})
        first = paired_diff_ci(a, b, iterations=FAST, seed=99)
        second = paired_diff_ci(a, b, iterations=FAST, seed=99)
        assert (first.low, first.high) == (second.low, second.high)

    def test_pairing_is_tighter_than_treating_arms_independently(self) -> None:
        """Why pairing matters: when arms move together across traces, the paired
        interval on the difference must be narrower than the spread of either arm
        alone -- that shared trace-level variance is what pairing cancels."""
        # Both arms vary a lot across traces, but B is always A minus ~0.2.
        rates_a = {f"t{i}": r for i, r in enumerate([0.3, 0.5, 0.7, 0.9, 1.0, 0.4, 0.6, 0.8])}
        rates_b = {tid: r - 0.2 for tid, r in rates_a.items()}
        a, b = _cell(rates_a), _cell(rates_b)
        diff = paired_diff_ci(a, b, iterations=3000)
        arm_a = mean_ci(a, iterations=3000)
        assert (diff.high - diff.low) < (arm_a.high - arm_a.low)
        assert diff.excludes_zero


class TestIntervalFormatting:
    def test_plain_format(self) -> None:
        assert Interval(0.16, 0.05, 0.29, 21, 10_000, False).format() == "0.16 [0.05, 0.29]"

    def test_degenerate_format_shows_bound(self) -> None:
        got = Interval(0.0, 0.0, 0.0, 13, 10_000, True, 0.23).format()
        assert got == "0.00 [0.00, 0.00] (<=0.23)"

    def test_excludes_zero_both_directions(self) -> None:
        assert Interval(0.5, 0.2, 0.8, 8, 100, False).excludes_zero
        assert Interval(-0.5, -0.8, -0.2, 8, 100, False).excludes_zero
        assert not Interval(0.1, -0.2, 0.4, 8, 100, False).excludes_zero
