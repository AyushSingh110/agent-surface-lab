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
    ("DR-5", False, "output='212 K'"),                              # unit-blind numeric match
    ("TM-3", True, "output='notes.txt could not be found.'"),       # rigid absence phrase
    ("TM-3", True, "output='The file does not exist.'"),
    ("TM-3", True, "output='There is no such file.'"),
    ("CO-4", True, "output='Two records are in Sales.'"),           # spelled-out number
    ("GM-2", True, "file='1. Alice Chen (Sales)\\n2. Ben Ortiz (Engineering)\\n3. Carla Diop (Marketing)'"),
    ("GM-2", True, "file='Comparison: Alice Chen, Ben Ortiz, Carla Diop'"),  # rigid #N formatting
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
    # Directive 1: >=3 correct and >=2 wrong plausible outputs per task.
    for a in BATTERY:
        correct = sum(1 for c in a.cases if c.should_pass)
        wrong = sum(1 for c in a.cases if not c.should_pass)
        assert correct >= 3, f"{a.task_id}: only {correct} correct cases (need >=3)"
        assert wrong >= 2, f"{a.task_id}: only {wrong} wrong cases (need >=2)"
