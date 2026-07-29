"""Recovery metrics: recovery rate (distribution over N) and the iatrogenic rate.

A wrong metric silently invalidates the paper, so this module is pure,
dependency-free arithmetic over recorded replay outcomes and is tested explicitly
in `tests/test_metrics.py`. No model calls, no I/O.

Definitions used throughout:
- A *cell* is one (intervention, failure_class). A *trace's cell rate* is its
  fraction of successful replays (successes / n).
- Recovery rate for a cell = the MACRO mean of per-trace rates (each trace weighted
  equally, so a trace with more replays does not dominate).
- Iatrogenic rate for (intervention vs no_op), per class = the fraction of traces
  whose intervention rate is strictly LESS than that same trace's no_op rate — i.e.
  intervening made recovery less likely than doing nothing. This paired,
  against-control definition is the study's central quantity (post-DoVer reframe).
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ReplayOutcome:
    """The result of N replays for one (trace, intervention) at its failure class.

    Attributes:
        trace_id: Identifies the trace, for pairing intervention vs no_op.
        failure_class: The oracle failure class of the trace (a matrix row).
        intervention: The intervention name (a matrix column).
        successes: Number of successful replays.
        n: Total replays (>= 1). successes must be in [0, n].
    """

    trace_id: str
    failure_class: str
    intervention: str
    successes: int
    n: int

    def __post_init__(self) -> None:
        if self.n < 1:
            raise ValueError(f"n must be >= 1, got {self.n}")
        if not 0 <= self.successes <= self.n:
            raise ValueError(f"successes {self.successes} out of range for n={self.n}")

    @property
    def rate(self) -> float:
        """This trace's per-cell recovery rate (successes / n)."""
        return self.successes / self.n


def mean_recovery(outcomes: list[ReplayOutcome]) -> float:
    """Macro mean recovery rate over traces (each trace weighted equally).

    Raises:
        ValueError: on an empty list — an undefined mean must not be silently 0.
    """
    if not outcomes:
        raise ValueError("mean_recovery requires at least one outcome")
    return sum(o.rate for o in outcomes) / len(outcomes)


def _index_by_trace(outcomes: list[ReplayOutcome], label: str) -> dict[str, ReplayOutcome]:
    """Index outcomes by trace_id, failing loudly on duplicates."""
    out: dict[str, ReplayOutcome] = {}
    for o in outcomes:
        if o.trace_id in out:
            raise ValueError(f"duplicate trace_id {o.trace_id!r} in {label} outcomes")
        out[o.trace_id] = o
    return out


def _pair(
    intervention_outcomes: list[ReplayOutcome],
    noop_outcomes: list[ReplayOutcome],
) -> list[tuple[ReplayOutcome, ReplayOutcome]]:
    """Pair each intervention outcome with the same trace's no_op outcome.

    Fails loudly if the trace sets differ: an unpaired comparison would silently
    bias the iatrogenic rate.
    """
    inter = _index_by_trace(intervention_outcomes, "intervention")
    noop = _index_by_trace(noop_outcomes, "no_op")
    if set(inter) != set(noop):
        missing = set(inter) ^ set(noop)
        raise ValueError(f"intervention/no_op traces do not match; unpaired: {sorted(missing)}")
    return [(inter[tid], noop[tid]) for tid in inter]


def iatrogenic_rate(
    intervention_outcomes: list[ReplayOutcome],
    noop_outcomes: list[ReplayOutcome],
) -> float:
    """Fraction of traces where the intervention recovers LESS often than no_op.

    Strict inequality: a tie (intervention == no_op) is not iatrogenic. Both lists
    must cover the same trace set (paired comparison).
    """
    pairs = _pair(intervention_outcomes, noop_outcomes)
    harmed = sum(1 for inter, noop in pairs if inter.rate < noop.rate)
    return harmed / len(pairs)


def net_improvement(
    intervention_outcomes: list[ReplayOutcome],
    noop_outcomes: list[ReplayOutcome],
) -> float:
    """Mean(intervention rate) - mean(no_op rate), paired over the same traces.

    Positive means the intervention helps on average; negative means it is net
    harmful relative to doing nothing.
    """
    pairs = _pair(intervention_outcomes, noop_outcomes)
    return sum(inter.rate - noop.rate for inter, noop in pairs) / len(pairs)


def is_near_boundary(
    outcome: ReplayOutcome, boundary: float = 0.5, z: float = 1.0
) -> bool:
    """Whether a cell's rate is close enough to a decision boundary to warrant more N.

    Uses a normal-approximation standard error of the per-trace rate: the cell is
    "near" the boundary when |rate - boundary| < z * sqrt(p(1-p)/n). This gives the
    §8-item-10 "raise N per-cell near a decision boundary" trigger a principled form
    rather than a magic constant: a rate of exactly 0 or 1 has zero SE and is never
    near, while a 1/3-vs-2/3 split at small n correctly flags for more sampling.

    Args:
        outcome: The cell outcome to test.
        boundary: The decision threshold (default 0.5).
        z: How many standard errors define "near" (default 1.0).

    Returns:
        True if more replays are advisable for this cell.
    """
    p = outcome.rate
    se = math.sqrt(p * (1.0 - p) / outcome.n)
    return abs(p - boundary) < z * se


def recovery_matrix(
    outcomes: list[ReplayOutcome],
) -> dict[tuple[str, str], float]:
    """Build the headline matrix: (intervention, failure_class) -> mean recovery.

    Each cell is the macro mean recovery over the traces of that class under that
    intervention. Returns an empty dict for empty input (a matrix with no cells),
    which is distinct from a cell with a defined-but-zero rate.
    """
    buckets: dict[tuple[str, str], list[ReplayOutcome]] = {}
    for o in outcomes:
        buckets.setdefault((o.intervention, o.failure_class), []).append(o)
    return {cell: mean_recovery(os) for cell, os in buckets.items()}
