"""Regression guard for the adversarial verifier audit (Directive 1).

The battery in `recovery_sandbox.audit_battery` exercises every task's verifier with
several correct phrasings and several wrong near-misses. This test freezes the set of
KNOWN gaps (verifiers that currently misclassify a case) so that:
  - any NEW gap (a fresh false-negative/false-positive) fails the suite immediately, and
  - fixing a known gap changes the set and forces this list to be updated.

The known gaps are documented, awaiting approved hardened rules (ground truth =
decision 4). Until they are fixed, all pilot numbers are PROVISIONAL.
"""
from __future__ import annotations

from pathlib import Path

from recovery_sandbox.audit_battery import BATTERY, run_audit
from recovery_sandbox.tasks import KILL_TEST_TASKS

# (task_id, expected_pass, detail) for each currently-misclassified case.
# expected_pass=True  -> a CORRECT answer wrongly scored as failure (false-negative)
# expected_pass=False -> a WRONG answer wrongly scored as pass (false-positive)
KNOWN_GAPS = {
    # RESIDUAL LIMITATIONS (accepted, documented — not fixed, because every
    # tightening we could apply would trade these rare false positives for far more
    # common false negatives on legitimate answers):
    #
    # 1. Any-number-token matching: an output that contains the correct value as an
    #    INTERMEDIATE while asserting a different final answer still passes. Fixing it
    #    would require guessing which number is "the answer" (e.g. last-number-wins),
    #    which breaks legitimate phrasings like "100 C equals 212 F".
    ("TM-5", False, "output='14.2857 rounds to 14.30'"),
    # 2. Extra spurious values in a multi-value answer are not penalized. Requiring
    #    "no extra numbers" would reject legitimate answers that restate the inputs
    #    (e.g. "10C=50F, 20C=68F, ...").
    ("CO-5", False, "output='50, 68, 86, 104, 122'"),
}


def test_no_new_verifier_gaps(tmp_path: Path) -> None:
    mismatches = run_audit(tmp_path)
    found = {(m.task_id, m.expected_pass, m.detail) for m in mismatches}
    new_gaps = found - KNOWN_GAPS
    fixed_gaps = KNOWN_GAPS - found
    assert not new_gaps, f"NEW verifier gaps introduced: {new_gaps}"
    assert not fixed_gaps, f"KNOWN gaps no longer present — update KNOWN_GAPS: {fixed_gaps}"


def test_battery_covers_every_task() -> None:
    covered = {a.task_id for a in BATTERY}
    all_ids = {t.id for t in KILL_TEST_TASKS}
    assert covered == all_ids, f"battery missing tasks: {all_ids - covered}"


def test_battery_has_enough_cases_per_task() -> None:
    # Rebalanced: >=3 correct and >=4 wrong per task. Wrong coverage is deliberately
    # heavier than correct coverage because false positives (wrong scored as correct)
    # silently inflate recovery rates, whereas false negatives are visible.
    for a in BATTERY:
        correct = sum(1 for c in a.cases if c.should_pass)
        wrong = sum(1 for c in a.cases if not c.should_pass)
        assert correct >= 3, f"{a.task_id}: only {correct} correct cases (need >=3)"
        assert wrong >= 4, f"{a.task_id}: only {wrong} wrong cases (need >=4)"
