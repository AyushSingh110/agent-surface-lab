"""Attach bootstrap confidence intervals to the firm-up recovery tables.

Pure re-analysis of `recovery_firm/cells.jsonl` -- no model calls, no new replays.
Every cell in that checkpoint stores its full per-replay boolean list (`dist`), which
is exactly what a two-level bootstrap needs, so the intervals come from data already
on disk.

What this produces:
  1. Skipped-lookup recovery by arm x chain depth, each with a 95% CI.
  2. Surface-form recovery by arm x form (date/hhmm), each with a 95% CI.
  3. The PAIRED contrasts the paper's claims actually rest on -- most importantly
     `lookup_permitting - declarative_neutral` per depth (the action-licensing
     claim) and every arm minus `no_op` (net improvement, the iatrogenic direction).

Point estimates are recomputed here and must reproduce the published table exactly;
any drift means the tables and the intervals describe different quantities.

Usage:
    python paper-recovery/analysis_ci.py --run data/v2batch --iterations 10000
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from harness.bootstrap import Interval, mean_ci, paired_diff_ci
from recovery_sandbox.v2_tasks import V2_TASKS

DEPTH = {t.id: t.trigger_depth for t in V2_TASKS}

# Mirrors run_recovery_firm.SF_FORM. Surface form is a property of the probe design
# rather than of the task dataclass, so it lives as a mapping in both places; if a
# new surface-form task is added it must be added to both.
SF_FORM = {"SM-01": "date", "SM-02": "date", "SM-03": "date", "SM-04": "date", "SM-05": "date",
           "SF-01": "hhmm", "SF-02": "hhmm", "SF-04": "version"}

CONTROL = "no_op"
LICENSING = "req_declarative_lookup_permitting"
NEUTRAL = "req_declarative_neutral"

SL_ARMS = ["no_op", "reflect_and_retry", "req_imperative_only", "req_imperative_plain",
           NEUTRAL, LICENSING]
SF_ARMS = ["no_op", "reflect_and_retry", "rollback_2", "restart_clean",
           "req_imperative_only", "req_imperative_plain", NEUTRAL, LICENSING]
DEPTHS = (1, 2, 3)
FORMS = ("date", "hhmm")

# (arm, subgroup) -> {trace_id: dist}
Grouped = dict[tuple[str, object], dict[str, list[bool]]]


def _task_of(trace_id: str) -> str:
    """Task id from a trace id (`SL-06-r30` -> `SL-06`)."""
    return trace_id.split("-r")[0]


def load_cells(run_dir: Path) -> tuple[Grouped, Grouped]:
    """Load the firm-up checkpoint and group it for analysis.

    Args:
        run_dir: The batch directory containing `recovery_firm/cells.jsonl`.

    Returns:
        (skipped_lookup grouped by (arm, depth), surface_form grouped by (arm, form)).

    Raises:
        FileNotFoundError: if the checkpoint is missing.
        ValueError: if a cell's recorded `successes` disagrees with its `dist`, which
            would mean the checkpoint was written inconsistently and no number from
            it can be trusted.
    """
    path = run_dir / "recovery_firm" / "cells.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"no firm-up checkpoint at {path}")

    sl: Grouped = defaultdict(dict)
    sf: Grouped = defaultdict(dict)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        dist = rec["dist"]
        if sum(dist) != rec["successes"] or len(dist) != rec["n"]:
            raise ValueError(
                f"cell {rec['trace_id']}/{rec['intervention']}: dist disagrees with "
                f"successes={rec['successes']} n={rec['n']}"
            )
        task = _task_of(rec["trace_id"])
        if rec["failure_class"] == "skipped_lookup":
            sl[(rec["intervention"], DEPTH[task])][rec["trace_id"]] = dist
        elif rec["failure_class"] == "surface_form_misuse":
            sf[(rec["intervention"], SF_FORM[task])][rec["trace_id"]] = dist
    return dict(sl), dict(sf)


def _ci_table(grouped: Grouped, arms: list[str], subgroups: tuple, iterations: int,
              seed: int) -> dict[str, dict[str, Interval]]:
    """Compute a CI for every (arm, subgroup) cell that has data."""
    out: dict[str, dict[str, Interval]] = {}
    for arm in arms:
        row: dict[str, Interval] = {}
        for sub in subgroups:
            cell = grouped.get((arm, sub))
            if cell:
                row[str(sub)] = mean_ci(cell, iterations=iterations, seed=seed)
        if row:
            out[arm] = row
    return out


def _contrasts(grouped: Grouped, arms: list[str], subgroups: tuple, reference: str,
               iterations: int, seed: int) -> dict[str, dict[str, Interval]]:
    """Paired differences of each arm against `reference`, per subgroup.

    Restricted to the traces the two arms share: arms were run on different breadth
    subsets (reflect/rollback/restart on n=8/8/6 vs the phrasing arms on n=21/23/6),
    so an unrestricted difference would compare different populations.
    """
    out: dict[str, dict[str, Interval]] = {}
    for arm in arms:
        if arm == reference:
            continue
        row: dict[str, Interval] = {}
        for sub in subgroups:
            cell = grouped.get((arm, sub))
            ref = grouped.get((reference, sub))
            if not cell or not ref:
                continue
            shared = set(cell) & set(ref)
            if not shared:
                continue
            row[str(sub)] = paired_diff_ci(
                {t: cell[t] for t in shared}, {t: ref[t] for t in shared},
                iterations=iterations, seed=seed,
            )
        if row:
            out[arm] = row
    return out


def _print_table(title: str, table: dict[str, dict[str, Interval]], subgroups: tuple,
                 label: str) -> None:
    print(f"\n=== {title} ===")
    header = f"{'arm':<36}" + "".join(f"{label}{s}".ljust(26) for s in subgroups)
    print(header)
    for arm, row in table.items():
        line = f"{arm:<36}"
        for sub in subgroups:
            ci = row.get(str(sub))
            line += (f"{ci.format()} (m={ci.n_traces})".ljust(26)) if ci else "-".ljust(26)
        print(line)


def _print_contrasts(title: str, table: dict[str, dict[str, Interval]], subgroups: tuple,
                     label: str) -> None:
    print(f"\n=== {title} ===")
    print(f"{'arm':<36}" + "".join(f"{label}{s}".ljust(30) for s in subgroups))
    for arm, row in table.items():
        line = f"{arm:<36}"
        for sub in subgroups:
            ci = row.get(str(sub))
            if ci:
                mark = "*" if ci.excludes_zero else " "
                line += f"{ci.point:+.2f} [{ci.low:+.2f},{ci.high:+.2f}]{mark}".ljust(30)
            else:
                line += "-".ljust(30)
        print(line)


def _serialise(table: dict[str, dict[str, Interval]]) -> dict:
    return {
        arm: {sub: {"point": ci.point, "low": ci.low, "high": ci.high,
                    "n_traces": ci.n_traces, "degenerate": ci.degenerate,
                    "conservative_upper": ci.conservative_upper,
                    "excludes_zero": ci.excludes_zero}
              for sub, ci in row.items()}
        for arm, row in table.items()
    }


def run(run_dir: Path, iterations: int, seed: int) -> None:
    """Compute and report every interval, then write them next to the raw cells."""
    sl, sf = load_cells(run_dir)
    print(f"loaded: skipped_lookup cells={len(sl)}  surface_form cells={len(sf)}")
    print(f"bootstrap: iterations={iterations}  seed={seed}  95% percentile intervals")

    sl_table = _ci_table(sl, SL_ARMS, DEPTHS, iterations, seed)
    sf_table = _ci_table(sf, SF_ARMS, FORMS, iterations, seed)
    sl_vs_noop = _contrasts(sl, SL_ARMS, DEPTHS, CONTROL, iterations, seed)
    sf_vs_noop = _contrasts(sf, SF_ARMS, FORMS, CONTROL, iterations, seed)

    _print_table("skipped_lookup: recovery by arm x depth (rate [95% CI])",
                 sl_table, DEPTHS, "depth ")
    _print_table("surface_form_misuse: recovery by arm x form (rate [95% CI])",
                 sf_table, FORMS, "")

    # The action-licensing claim IS this contrast: two declarative arms differing only
    # by the licensing clause. If its interval contains zero, the headline is not
    # statistically supported and must be restated.
    print("\n" + "=" * 74)
    print("HEADLINE CONTRAST — action-licensing (paired, * = CI excludes zero)")
    print("=" * 74)
    print(f"{'lookup_permitting - declarative_neutral':<36}")
    for depth in DEPTHS:
        lic, neu = sl.get((LICENSING, depth)), sl.get((NEUTRAL, depth))
        if not lic or not neu:
            continue
        shared = set(lic) & set(neu)
        ci = paired_diff_ci({t: lic[t] for t in shared}, {t: neu[t] for t in shared},
                            iterations=iterations, seed=seed)
        mark = "*" if ci.excludes_zero else "  (CONTAINS ZERO)"
        print(f"  depth {depth}: {ci.point:+.2f} [{ci.low:+.2f}, {ci.high:+.2f}] "
              f"m={ci.n_traces}{mark}")

    _print_contrasts("skipped_lookup: net improvement vs no_op (paired)",
                     sl_vs_noop, DEPTHS, "depth ")
    _print_contrasts("surface_form: net improvement vs no_op (paired)",
                     sf_vs_noop, FORMS, "")

    out = run_dir / "recovery_firm" / "confidence_intervals.json"
    out.write_text(json.dumps({
        "iterations": iterations, "seed": seed, "alpha": 0.05,
        "method": "two-level paired percentile bootstrap (traces, then replays)",
        "skipped_lookup": _serialise(sl_table),
        "surface_form": _serialise(sf_table),
        "skipped_lookup_vs_no_op": _serialise(sl_vs_noop),
        "surface_form_vs_no_op": _serialise(sf_vs_noop),
    }, indent=2), encoding="utf-8")
    print(f"\nwritten: {out}")


def main() -> None:
    p = argparse.ArgumentParser(description="Bootstrap CIs for the firm-up recovery tables.")
    p.add_argument("--run", type=Path, default=Path("data/v2batch"))
    p.add_argument("--iterations", type=int, default=10_000)
    p.add_argument("--seed", type=int, default=20260721)
    args = p.parse_args()
    run(args.run, args.iterations, args.seed)


if __name__ == "__main__":
    main()
