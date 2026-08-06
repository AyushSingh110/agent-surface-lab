"""Phase 2 analysis: does `action-licensing` survive identification?

Reads the three new factorial arms (`recovery_factorial/cells.jsonl`) together with the
two arms that share their base and were already run at N=10
(`recovery_firm/cells.jsonl`), assembles the 2x2, and reports paired bootstrap
contrasts.

**The decisive comparison is each arm against `fac_placebo`**, not against `no_op`.
The placebo is length-matched and adds a second clause that grants nothing and names
nothing, so a difference from it isolates what the clause SAYS from the mere fact that
a clause is present. Comparing against no_op instead would leave salience uncontrolled
-- the exact confound this phase exists to remove.

Verdict logic (printed at the end, but the interpretation is the human's call):
  - licensing effect present, tool-mention effect absent  -> C2 confirmed and identified
  - tool-mention effect present, licensing effect absent  -> C2 refuted; tool-mention priming
  - placebo itself high vs the no-clause control          -> generic second-clause salience
  - both effects present                                  -> report both, check interaction

Usage:
    python paper-recovery/analysis_factorial.py --run data/v2batch
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from harness.bootstrap import mean_ci, paired_diff_ci

PLACEBO = "fac_placebo"
LICENSE_NO_TOOL = "fac_license_no_tool"
TOOL_NO_LICENSE = "fac_tool_no_license"
BOTH = "req_declarative_lookup_permitting"   # licenses + mentions tools (from firm-up)
NO_CLAUSE = "req_imperative_plain"           # same base, no trailing clause (from firm-up)

# Factor levels, kept here so the table can be assembled without re-parsing prompts.
LEVELS = {
    BOTH: (True, True),
    LICENSE_NO_TOOL: (True, False),
    TOOL_NO_LICENSE: (False, True),
    PLACEBO: (False, False),
}
ORDER = [BOTH, LICENSE_NO_TOOL, TOOL_NO_LICENSE, PLACEBO, NO_CLAUSE]

CellDists = dict[str, list[bool]]


def load(run_dir: Path) -> dict[str, CellDists]:
    """Load factorial arms plus the two reused firm-up arms, keyed by arm name.

    Only skipped-lookup cells are taken from the firm-up file, since that is the pool
    the factorial runs on.

    Raises:
        FileNotFoundError: if the factorial run has not been executed yet.
    """
    fac_path = run_dir / "recovery_factorial" / "cells.jsonl"
    if not fac_path.is_file():
        raise FileNotFoundError(
            f"no factorial cells at {fac_path} -- run paper-recovery/run_factorial.py first"
        )

    arms: dict[str, CellDists] = defaultdict(dict)
    for line in fac_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            arms[rec["intervention"]][rec["trace_id"]] = rec["dist"]

    firm_path = run_dir / "recovery_firm" / "cells.jsonl"
    for line in firm_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec["failure_class"] == "skipped_lookup" and rec["intervention"] in (BOTH, NO_CLAUSE):
            arms[rec["intervention"]][rec["trace_id"]] = rec["dist"]
    return dict(arms)


def _shared(a: CellDists, b: CellDists) -> tuple[CellDists, CellDists]:
    """Restrict two arms to the traces they share, so contrasts stay paired."""
    common = set(a) & set(b)
    return {t: a[t] for t in common}, {t: b[t] for t in common}


def _pooled(arms: dict[str, CellDists], names: list[str]) -> CellDists:
    """Pool several arms into one pseudo-cell for a main effect.

    Each trace's rate is averaged across the pooled arms, so a trace still contributes
    once and the macro-mean weighting is preserved.
    """
    traces = set.intersection(*(set(arms[n]) for n in names))
    pooled: CellDists = {}
    for t in traces:
        # Concatenating the replay lists averages the arms while keeping the
        # resampling unit (this trace) intact for the bootstrap.
        merged: list[bool] = []
        for n in names:
            merged.extend(arms[n][t])
        pooled[t] = merged
    return pooled


def run(run_dir: Path, iterations: int, seed: int) -> None:
    """Report the 2x2, the contrasts against placebo, and the two main effects."""
    arms = load(run_dir)
    missing = [a for a in ORDER if a not in arms]
    if missing:
        print(f"WARNING: missing arms {missing}; some contrasts will be skipped\n")

    print("=" * 78)
    print("PHASE 2 — REPAIR-SURFACE FACTORIAL (skipped-lookup, N=10)")
    print("=" * 78)
    print(f"bootstrap: iterations={iterations} seed={seed}  95% paired percentile intervals\n")

    print(f"{'arm':<36}{'licenses':<10}{'tools':<8}{'recovery [95% CI]':<26}m")
    for arm in ORDER:
        if arm not in arms:
            continue
        lic, tool = LEVELS.get(arm, (False, False))
        tag = "(no clause)" if arm == NO_CLAUSE else ""
        ci = mean_ci(arms[arm], iterations=iterations, seed=seed)
        print(f"{arm:<36}{str(lic):<10}{str(tool):<8}{ci.format():<26}{ci.n_traces}  {tag}")

    # --- The decisive contrasts: against the length-matched placebo -----------------
    print("\n" + "-" * 78)
    print("CONTRASTS vs fac_placebo (length-matched; isolates clause CONTENT)")
    print("-" * 78)
    if PLACEBO in arms:
        for arm in (BOTH, LICENSE_NO_TOOL, TOOL_NO_LICENSE):
            if arm not in arms:
                continue
            a, b = _shared(arms[arm], arms[PLACEBO])
            ci = paired_diff_ci(a, b, iterations=iterations, seed=seed)
            verdict = "EXCLUDES ZERO" if ci.excludes_zero else "contains zero"
            print(f"  {arm:<36}{ci.point:+.2f} [{ci.low:+.2f}, {ci.high:+.2f}]  m={ci.n_traces}  {verdict}")

    # Does merely adding a clause do anything? placebo vs the no-clause control.
    if PLACEBO in arms and NO_CLAUSE in arms:
        a, b = _shared(arms[PLACEBO], arms[NO_CLAUSE])
        ci = paired_diff_ci(a, b, iterations=iterations, seed=seed)
        verdict = "EXCLUDES ZERO -> generic salience effect" if ci.excludes_zero else "contains zero -> no salience effect"
        print(f"\n  {'placebo - no_clause (salience check)':<36}"
              f"{ci.point:+.2f} [{ci.low:+.2f}, {ci.high:+.2f}]  m={ci.n_traces}  {verdict}")

    # --- Main effects over the 2x2 --------------------------------------------------
    print("\n" + "-" * 78)
    print("MAIN EFFECTS (pooled over the 2x2)")
    print("-" * 78)
    quad = [BOTH, LICENSE_NO_TOOL, TOOL_NO_LICENSE, PLACEBO]
    if all(a in arms for a in quad):
        lic_hi = _pooled(arms, [BOTH, LICENSE_NO_TOOL])
        lic_lo = _pooled(arms, [TOOL_NO_LICENSE, PLACEBO])
        tool_hi = _pooled(arms, [BOTH, TOOL_NO_LICENSE])
        tool_lo = _pooled(arms, [LICENSE_NO_TOOL, PLACEBO])
        for label, hi, lo in (("licensing", lic_hi, lic_lo), ("tool-mention", tool_hi, tool_lo)):
            a, b = _shared(hi, lo)
            ci = paired_diff_ci(a, b, iterations=iterations, seed=seed)
            verdict = "EXCLUDES ZERO" if ci.excludes_zero else "contains zero"
            print(f"  effect of {label:<22}{ci.point:+.2f} [{ci.low:+.2f}, {ci.high:+.2f}]  {verdict}")

        # Interaction: does licensing pay off differently when tools are named?
        a1, b1 = _shared(arms[BOTH], arms[TOOL_NO_LICENSE])
        a2, b2 = _shared(arms[LICENSE_NO_TOOL], arms[PLACEBO])
        d1 = paired_diff_ci(a1, b1, iterations=iterations, seed=seed)
        d2 = paired_diff_ci(a2, b2, iterations=iterations, seed=seed)
        print(f"  licensing effect | tools named    {d1.point:+.2f} [{d1.low:+.2f}, {d1.high:+.2f}]")
        print(f"  licensing effect | tools unnamed  {d2.point:+.2f} [{d2.low:+.2f}, {d2.high:+.2f}]")
        print("  (non-overlapping intervals above would indicate an interaction)")
    else:
        print("  incomplete 2x2 -- run run_factorial.py to completion first")

    out = run_dir / "recovery_factorial" / "factorial_analysis.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "iterations": iterations, "seed": seed,
        "arms": {
            arm: {"licenses": LEVELS.get(arm, (None, None))[0],
                  "mentions_tools": LEVELS.get(arm, (None, None))[1],
                  **{k: v for k, v in vars(mean_ci(arms[arm], iterations=iterations, seed=seed)).items()}}
            for arm in ORDER if arm in arms
        },
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwritten: {out}")


def main() -> None:
    p = argparse.ArgumentParser(description="Analyse the Phase 2 repair-surface factorial.")
    p.add_argument("--run", type=Path, default=Path("data/v2batch"))
    p.add_argument("--iterations", type=int, default=10_000)
    p.add_argument("--seed", type=int, default=20260721)
    args = p.parse_args()
    run(args.run, args.iterations, args.seed)


if __name__ == "__main__":
    main()
