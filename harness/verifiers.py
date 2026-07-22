"""Deterministic ground-truth verifiers (decision §8 item 4).

Every verifier is a deterministic function of (trace, final_output) → bool — never
an LLM judge. Each maps to a task type: numeric/canonical → exact match; open QA →
fact-match; file/deliverable → file existence + content.

Two correctness rules matter here and are tested explicitly:
- **Numbers match as whole tokens, never as substrings.** GT "20" must NOT be
  satisfied by "2024"/"120"/"200"/"20.5". Numeric needles are compared by extracting
  full number tokens and testing equality (within tol), not `in`.
- **Text matches on non-alphanumeric boundaries**, so "#1" does not match "#10" and
  "Sales" is a whole word, while trailing punctuation ("not found.") still matches.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from harness.trace import TraceRecord

Verifier = Callable[[TraceRecord, str], bool]

# One number-token pattern shared by every numeric check.
_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_NUMERIC_STR = re.compile(r"-?\d+(?:\.\d+)?$")


def normalize_text(text: str) -> str:
    """Normalization rule used by every string verifier (and the search fixture).

    Rule (exactly this): strip ends, lowercase, then collapse any run of
    whitespace-or-commas into a single space. Text matching is then boundary-aware
    (see `_contains`), not raw substring. This is the one place the rule lives, so
    tool fixtures and verifiers can never disagree about what "matches".
    """
    return re.sub(r"[\s,]+", " ", text.strip().lower())


def _numbers_in(text: str) -> list[float]:
    """Full number tokens in text, comma-grouping removed (so '4,200' → 4200)."""
    return [float(tok) for tok in _NUM_RE.findall(text.replace(",", ""))]


def _text_contains(haystack_norm: str, needle_norm: str) -> bool:
    """Whether needle appears in haystack bounded by non-alphanumeric characters.

    Boundaries are letters/digits only, so punctuation (".", "-", "#") counts as a
    boundary: "#1" won't match inside "#10", but "not found." still matches "not found".
    """
    pattern = r"(?<![a-z0-9])" + re.escape(needle_norm) + r"(?![a-z0-9])"
    return re.search(pattern, haystack_norm) is not None


def _contains(haystack_norm: str, needle_norm: str, tol: float) -> bool:
    """Boundary/token-aware containment: numeric needles match as whole numbers."""
    if _NUMERIC_STR.match(needle_norm):
        target = float(needle_norm)
        return any(abs(n - target) <= tol for n in _numbers_in(haystack_norm))
    return _text_contains(haystack_norm, needle_norm)


def numeric_exact(expected: float, tol: float = 1e-9) -> Verifier:
    """Verifier: some full number token in the output equals `expected` (within tol).

    Token-based (not substring), so "2024" never satisfies a GT of 20.
    """

    def _verify(trace: TraceRecord, final_output: str) -> bool:
        return any(abs(n - expected) <= tol for n in _numbers_in(final_output))

    return _verify


def fact_match(expected: str, tol: float = 0.0) -> Verifier:
    """Verifier: the expected string appears in the output (boundary/token-aware).

    A numeric `expected` is matched as a whole number; text is matched on
    non-alphanumeric boundaries. Never a raw substring test.
    """
    target = normalize_text(expected)

    def _verify(trace: TraceRecord, final_output: str) -> bool:
        return _contains(normalize_text(final_output), target, tol)

    return _verify


def file_written(path: str | Path, expected_content: str, tol: float = 0.0) -> Verifier:
    """Verifier: a file exists at `path` and contains the expected content.

    Content matching uses the same boundary/token rule as `fact_match`, so a file
    holding "2024" does not satisfy an expected "20".
    """
    p = Path(path)
    target = normalize_text(expected_content)

    def _verify(trace: TraceRecord, final_output: str) -> bool:
        if not p.is_file():
            return False
        return _contains(normalize_text(p.read_text(encoding="utf-8")), target, tol)

    return _verify


def no_fabricated_number(trace: TraceRecord, final_output: str) -> bool:
    """True iff the output introduces no number/date that was not in the task prompt.

    Numbers echoed from the prompt (e.g. a year named in the question) are allowed, so
    an honest "no 2025 figure found" still passes; any new figure is fabrication.
    """
    prompt_numbers = set(_numbers_in(trace.task))
    return all(n in prompt_numbers for n in _numbers_in(final_output))


# Magnitude words that signal a spelled-out quantity (e.g. "about five million").
_MAGNITUDE_WORDS = ("hundred", "thousand", "million", "billion", "trillion")


def no_fabricated_value(trace: TraceRecord, final_output: str) -> bool:
    """Robust hallucination check: correct iff the output asserts no specific value
    the prompt did not supply — neither a fabricated number/date NOR a spelled-out
    magnitude ("about five million").

    This replaces the earlier honesty-phrase list, which produced false negatives:
    honest answers like "did not yield any results" or "could not be found" were
    scored as failures merely because they used a phrasing not on the list. Here,
    correctness is defined by the ABSENCE of a fabricated value, so any honest
    acknowledgement — in any wording — passes, while an invented figure (digits or a
    magnitude word not present in the prompt) fails. Numbers/words echoed from the
    prompt are allowed.
    """
    if not no_fabricated_number(trace, final_output):
        return False
    prompt_norm = normalize_text(trace.task)
    out_norm = normalize_text(final_output)
    for word in _MAGNITUDE_WORDS:
        if _text_contains(out_norm, word) and not _text_contains(prompt_norm, word):
            return False
    return True


def all_of(*verifiers: Verifier) -> Verifier:
    """Conjunction: succeeds only if every sub-verifier succeeds (deterministic)."""
    if not verifiers:
        raise ValueError("all_of requires at least one verifier")

    def _verify(trace: TraceRecord, final_output: str) -> bool:
        return all(v(trace, final_output) for v in verifiers)

    return _verify


def any_of(*verifiers: Verifier) -> Verifier:
    """Disjunction: succeeds if any sub-verifier succeeds (deterministic)."""
    if not verifiers:
        raise ValueError("any_of requires at least one verifier")

    def _verify(trace: TraceRecord, final_output: str) -> bool:
        return any(v(trace, final_output) for v in verifiers)

    return _verify
