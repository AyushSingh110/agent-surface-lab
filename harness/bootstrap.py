from __future__ import annotations
import random
from dataclasses import dataclass

DEFAULT_ITERATIONS = 10_000
DEFAULT_ALPHA = 0.05

# Trace id -> that trace's per-replay success flags under one intervention.
CellDists = dict[str, list[bool]]


@dataclass(frozen=True)
class Interval:
    """A point estimate with its bootstrap confidence interval.

    Attributes:
        point: The observed macro mean over traces (matches `metrics.mean_recovery`).
        low: Lower percentile bound.
        high: Upper percentile bound.
        n_traces: Number of traces the cell rests on -- the real sample size.
        iterations: Bootstrap iterations used.
        degenerate: True when every resample gives the same value (all-zero or
            all-one cells). The interval is a point, and `conservative_upper`
            carries the honest bound instead.
        conservative_upper: Cluster-level rule-of-three upper bound, set only for
            all-zero degenerate cells; None otherwise.
    """

    point: float
    low: float
    high: float
    n_traces: int
    iterations: int
    degenerate: bool
    conservative_upper: float | None = None

    def format(self, places: int = 2) -> str:
        """Render as `0.16 [0.05, 0.29]`, or with the bound for degenerate cells."""
        base = f"{self.point:.{places}f} [{self.low:.{places}f}, {self.high:.{places}f}]"
        if self.degenerate and self.conservative_upper is not None:
            return f"{base} (<={self.conservative_upper:.{places}f})"
        return base

    @property
    def excludes_zero(self) -> bool:
        """Whether the interval lies strictly on one side of zero.

        Used for difference intervals: True means the contrast survives resampling
        in a consistent direction.
        """
        return self.low > 0.0 or self.high < 0.0


def rule_of_three_upper(n_traces: int) -> float:
    """Conservative 95% upper bound on a rate when zero events were observed.

    The rule of three states that after n independent trials with no events, the
    95% upper bound on the true rate is approximately 3/n. Here the independent
    unit is the TRACE, not the replay: N replays of one trace share that trace's
    prompt, tools and failure step, so they are not independent trials. Using
    3/(m*N) would claim far more precision than a clustered design supports, so
    this deliberately uses the smaller, more conservative 3/m.

    Args:
        n_traces: Number of independent traces observed with zero recoveries.

    Returns:
        The upper bound, capped at 1.0 (it exceeds 1 for m < 3).

    Raises:
        ValueError: if n_traces < 1.
    """
    if n_traces < 1:
        raise ValueError(f"n_traces must be >= 1, got {n_traces}")
    return min(1.0, 3.0 / n_traces)


def _percentile(sorted_values: list[float], q: float) -> float:
    """Linear-interpolated percentile of an already-sorted list. q in [0, 1]."""
    if not sorted_values:
        raise ValueError("percentile of an empty list is undefined")
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = pos - lo
    return sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac


def _resample_rate(dist: list[bool], rng: random.Random) -> float:
    """Resample one trace's replay outcomes with replacement; return its rate."""
    n = len(dist)
    return sum(rng.choices(dist, k=n)) / n


def _macro_mean(dists: CellDists) -> float:
    """Observed macro mean over traces (each trace weighted equally)."""
    return sum(sum(d) / len(d) for d in dists.values()) / len(dists)


def _validate(dists: CellDists, label: str) -> None:
    """Reject empty cells and empty replay lists loudly rather than returning NaN."""
    if not dists:
        raise ValueError(f"{label}: no traces; a bootstrap over an empty cell is undefined")
    for trace_id, dist in dists.items():
        if not dist:
            raise ValueError(f"{label}: trace {trace_id!r} has no replays")


def mean_ci(
    dists: CellDists,
    iterations: int = DEFAULT_ITERATIONS,
    alpha: float = DEFAULT_ALPHA,
    seed: int = 20260721,
) -> Interval:
    """Two-level bootstrap CI for one cell's macro recovery rate.

    Args:
        dists: Trace id -> per-replay success flags for this (arm, subgroup) cell.
        iterations: Bootstrap resamples.
        alpha: Two-sided significance level (0.05 -> a 95% interval).
        seed: RNG seed; the same seed reproduces the interval exactly.

    Returns:
        An `Interval`. All-zero cells are flagged degenerate and carry a
        cluster-level rule-of-three upper bound.

    Raises:
        ValueError: on an empty cell or a trace with no replays.
    """
    _validate(dists, "mean_ci")
    rng = random.Random(seed)
    trace_ids = list(dists)
    m = len(trace_ids)
    point = _macro_mean(dists)

    stats: list[float] = []
    for _ in range(iterations):
        drawn = rng.choices(trace_ids, k=m)
        stats.append(sum(_resample_rate(dists[t], rng) for t in drawn) / m)
    stats.sort()

    low = _percentile(stats, alpha / 2.0)
    high = _percentile(stats, 1.0 - alpha / 2.0)
    degenerate = low == high
    # Only an all-zero cell gets a rule-of-three bound; an all-one cell's honest
    # statement is a lower bound, which no current table needs.
    upper = rule_of_three_upper(m) if degenerate and point == 0.0 else None
    return Interval(point, low, high, m, iterations, degenerate, upper)


def paired_diff_ci(
    dists_a: CellDists,
    dists_b: CellDists,
    iterations: int = DEFAULT_ITERATIONS,
    alpha: float = DEFAULT_ALPHA,
    seed: int = 20260721,
) -> Interval:
    """Two-level PAIRED bootstrap CI for (macro mean of A) - (macro mean of B).

    Both arms must cover the same trace set: an unpaired difference would silently
    compare different populations, the same failure mode `metrics._pair` guards
    against. Each iteration draws one set of trace indices and evaluates both arms
    on it, preserving trace-level correlation.

    Args:
        dists_a: Trace id -> replay flags for the first arm (the one expected higher).
        dists_b: Trace id -> replay flags for the second arm (the comparison/control).
        iterations: Bootstrap resamples.
        alpha: Two-sided significance level.
        seed: RNG seed.

    Returns:
        An `Interval` whose `point` is the observed difference. Check
        `excludes_zero` to see whether the contrast survives resampling.

    Raises:
        ValueError: if the trace sets differ, or either cell is empty.
    """
    _validate(dists_a, "paired_diff_ci(a)")
    _validate(dists_b, "paired_diff_ci(b)")
    if set(dists_a) != set(dists_b):
        unpaired = set(dists_a) ^ set(dists_b)
        raise ValueError(f"paired_diff_ci requires identical trace sets; unpaired: {sorted(unpaired)}")

    rng = random.Random(seed)
    trace_ids = list(dists_a)
    m = len(trace_ids)
    point = _macro_mean(dists_a) - _macro_mean(dists_b)

    stats: list[float] = []
    for _ in range(iterations):
        drawn = rng.choices(trace_ids, k=m)
        a = sum(_resample_rate(dists_a[t], rng) for t in drawn) / m
        b = sum(_resample_rate(dists_b[t], rng) for t in drawn) / m
        stats.append(a - b)
    stats.sort()

    low = _percentile(stats, alpha / 2.0)
    high = _percentile(stats, 1.0 - alpha / 2.0)
    return Interval(point, low, high, m, iterations, degenerate=low == high)
