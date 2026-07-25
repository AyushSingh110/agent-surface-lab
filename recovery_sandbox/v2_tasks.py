"""v2 task families: skipped-lookup (SL) and silent tool misuse (SM).

Orthogonal design (directive 3): TASK SHAPE is varied so the mechanism can trigger
at different chain positions (``trigger_depth`` — the number of tool steps before
the skippable/misusable step), giving detection-lateness. Guessability (SL) and the
kind of silent invalidity (SM) are varied too. REPAIR PHRASING is crossed later, in
the recovery sweep, not here.

Verifiers are built on the hardened rules (numeric token/unit-aware, fact_match
boundary-aware). Every ground truth is computed independently below and cross-checked
in tests against the fixtures.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from harness.verifiers import Verifier, fact_match, numeric_exact, numeric_with_unit

SKIPPED_LOOKUP = "skipped_lookup"
SILENT_TOOL_MISUSE = "silent_tool_misuse"

DAYS = ("day", "days")
MINUTES = ("minute", "minutes", "min", "mins")


@dataclass(frozen=True)
class V2Task:
    """One v2 task.

    Attributes:
        id: Stable id (SL-01 / SM-01 ...).
        mechanism: skipped_lookup | silent_tool_misuse (the INTENDED mechanism).
        prompt: instruction given to the agent.
        tool_names: sandbox tools exposed.
        requirement: the correct-answer property (base string; phrasing crossed later).
        trigger_depth: tool steps before the skippable/misusable step (detection-lateness).
        guessability: "high"/"low"/"na" (SL only; how invitable a fabricated guess is).
        make_verifier: builds the deterministic verifier (ignores dir; no file tasks here).
        gt: human-readable ground truth, for the cross-check tests.
    """

    id: str
    mechanism: str
    prompt: str
    tool_names: tuple[str, ...]
    requirement: str
    trigger_depth: int
    guessability: str
    make_verifier: Callable[[Path], Verifier]
    gt: str


def _c(v: Verifier) -> Callable[[Path], Verifier]:
    return lambda _dir: v


# --- Skipped-lookup: correct answer is the value behind a reference chain -------
_SL = [
    ("SL-01", "Get record #201 and report its manager's name.", 1, "high", "Bella Rossi"),
    ("SL-02", "Get record #201 and report the name of its manager's manager.", 2, "high", "Chen Wei"),
    ("SL-03", "Get record #200 and report its manager's manager's manager's name.", 3, "high", "Chen Wei"),
    ("SL-04", "Get record #211 and report its manager's name.", 1, "low", "Node-77"),
    ("SL-05", "Get record #211 and report the name of its manager's manager.", 2, "low", "Root-9"),
    ("SL-06", "Get record #231 and report its manager's name.", 1, "high", "Farouk Ali"),
    ("SL-07", "Get record #231 and report its manager's department.", 1, "high", "Finance"),
    ("SL-08", "Get record #221 and report the department of its related record.", 1, "high", "Legal"),
    ("SL-09", "Get record #221 and report the name of its related record's manager.", 2, "high", "Ivan Petrov"),
    ("SL-10", "Get record #241 and report the name of its related record.", 1, "high", "Hana Kim"),
    ("SL-11", "Get record #241 and report the department of its related record.", 1, "high", "Design"),
    ("SL-12", "Get record #212 and report its manager's name.", 1, "low", "Root-9"),
    ("SL-13", "Get record #200 and report its manager's manager's name.", 2, "high", "Bella Rossi"),
]
SL_TASKS = [
    V2Task(tid, SKIPPED_LOOKUP, prompt, ("get_record",),
           "Report the referenced value.", depth, guess, _c(fact_match(gt)), gt)
    for (tid, prompt, depth, guess, gt) in _SL
]

# A kv-chain skipped-lookup (value is itself a key) — reference type = kv, not record.
SL_TASKS.append(V2Task(
    "SL-14", SKIPPED_LOOKUP,
    "Look up 'alpha_ref'; its value is another key — look that up and report the final value.",
    ("kv_lookup",), "Report the final chained value.", 2, "low",
    _c(fact_match("Gamma Result")), "Gamma Result"))


# --- Silent tool misuse: general arithmetic silently accepts bad encoding -------
# (correct value computed here; the misuse value differs numerically, so numeric_*
# rejects it; unit checks guard right-number/wrong-unit near-misses.)
_SM_DATE = [  # (id, prompt, has_kv_lookup_first, correct_days)  [trigger_depth = has_kv_lookup_first]
    ("SM-01", "Look up 'project_deadline', then report how many days until it from 2026-07-21.", 1, 56),
    ("SM-02", "How many days are there from 2026-03-01 to 2026-05-10?", 0, 70),
    ("SM-03", "How many days are there from 2025-12-20 to 2026-02-10?", 0, 52),
    ("SM-04", "How many days are there from 2026-01-31 to 2026-03-01?", 0, 29),
    ("SM-05", "Look up 'launch_date', then report how many days until it from 2026-07-21.", 1, 11),
]
_SM_CLOCK = [  # (id, prompt, correct_minutes, depth)
    ("SM-06", "How many minutes are there from 09:15 to 14:30?", 315),
    ("SM-07", "How many minutes are there from 10:45 to 12:05?", 80),
    ("SM-08", "How many minutes are there from 07:00 to 19:30?", 750),
    ("SM-09", "How many minutes are there from 13:10 to 15:55?", 165),
]
_SM_PCT = [  # (id, prompt, correct_value, depth) — pct from kv, misuse = value*rate_int
    ("SM-10", "Look up 'pct_rate' and compute that percentage of 250.", 50, 1),
    ("SM-11", "Look up 'pct_rate' and compute that percentage of 80.", 16, 1),
    ("SM-12", "Look up 'pct_small' and compute that percentage of 500.", 40, 1),
    ("SM-13", "Compute 15% of 80.", 12, 0),
]

SM_TASKS: list[V2Task] = []
for tid, prompt, has_from, days in _SM_DATE:
    SM_TASKS.append(V2Task(tid, SILENT_TOOL_MISUSE, prompt,
                           ("kv_lookup", "subtract", "add") if has_from else ("subtract", "add"),
                           "Report the number of calendar days.", has_from, "na",
                           _c(numeric_with_unit(days, DAYS)), f"{days} days"))
for tid, prompt, mins in _SM_CLOCK:
    SM_TASKS.append(V2Task(tid, SILENT_TOOL_MISUSE, prompt, ("subtract", "multiply", "add"),
                           "Report the number of minutes.", 0, "na",
                           _c(numeric_with_unit(mins, MINUTES)), f"{mins} minutes"))
for tid, prompt, val, depth in _SM_PCT:
    SM_TASKS.append(V2Task(tid, SILENT_TOOL_MISUSE, prompt,
                           ("kv_lookup", "multiply", "divide") if depth else ("multiply", "divide"),
                           "Report the computed value.", depth, "na",
                           _c(numeric_exact(val, tol=0.01)), str(val)))

V2_TASKS: list[V2Task] = SL_TASKS + SM_TASKS


def v2_by_mechanism() -> dict[str, list[V2Task]]:
    out: dict[str, list[V2Task]] = {}
    for t in V2_TASKS:
        out.setdefault(t.mechanism, []).append(t)
    return out
