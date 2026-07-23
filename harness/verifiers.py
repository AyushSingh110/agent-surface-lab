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
    """Full DIGIT number tokens in text, comma-grouping removed (so '4,200' → 4200)."""
    return [float(tok) for tok in _NUM_RE.findall(text.replace(",", ""))]


# Spelled-out integers for numeric matching. Deliberately small/common; compound
# forms ("twenty two") are not parsed.
_SPELLED: dict[str, float] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20,
}


def _candidate_numbers(text: str) -> list[float]:
    """Numbers to compare against a numeric GT.

    Digits win: if the text contains ANY digit token, only digits are considered.
    Spelled-out integers are used ONLY when there is no digit at all. This is what
    makes GT=2 match "Two records" (no digits) while REJECTING "…two tools and found
    3 in Sales" (a digit '3' is present, so 'two' is ignored and 2 is absent). Without
    the digits-win rule, spelled numbers would reintroduce false positives — the
    dangerous direction.
    """
    digits = _numbers_in(text)
    if digits:
        return digits
    norm = normalize_text(text)
    return [v for word, v in _SPELLED.items() if _text_contains(norm, word)]


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
        return any(abs(n - target) <= tol for n in _candidate_numbers(haystack_norm))
    return _text_contains(haystack_norm, needle_norm)


def numeric_exact(expected: float, tol: float = 1e-9) -> Verifier:
    """Verifier: some full number token in the output equals `expected` (within tol).

    Token-based (not substring), so "2024" never satisfies a GT of 20. Spelled-out
    integers count only when no digit is present (see `_candidate_numbers`).

    NOTE (unit-blindness): this checks the NUMBER only. For any task where a wrong
    UNIT with the right number is a plausible wrong answer (temperature conversions),
    use `numeric_with_unit` instead — otherwise "212 K" would satisfy a 212°F GT
    (a false positive, the dangerous direction).
    """

    def _verify(trace: TraceRecord, final_output: str) -> bool:
        return any(abs(n - expected) <= tol for n in _candidate_numbers(final_output))

    return _verify


def numeric_with_unit(expected: float, units: tuple[str, ...], tol: float = 1e-9) -> Verifier:
    """Verifier: the right NUMBER *and* a required unit token both appear.

    Closes the unit-blind false positive: "212 K" fails a 212°F GT because no
    fahrenheit unit is present. A unit matches if any synonym appears bounded by
    non-letters (so "212f", "212 F.", and "fahrenheit" all count, but the 'f' in
    "of" does not).
    """
    if not units:
        raise ValueError("numeric_with_unit requires at least one unit synonym")

    def _verify(trace: TraceRecord, final_output: str) -> bool:
        norm = normalize_text(final_output)
        number_ok = any(abs(n - expected) <= tol for n in _candidate_numbers(final_output))
        unit_ok = any(re.search(rf"(?<![a-z]){re.escape(u)}(?![a-z])", norm) for u in units)
        return number_ok and unit_ok

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


# Negation-of-existence pattern: a negation token within a short gap of a
# finding/existence token. Robust to phrasing ("not found", "could not be found",
# "does not exist", "no such file", "unable to locate") — not a fixed phrase list.
_ABSENCE_RE = re.compile(
    r"(not|no|cannot|can ?not|could ?n[o']?t|couldn't|does ?n[o']?t|doesn't|do ?n[o']?t|"
    r"is ?n[o']?t|isn't|was ?n[o']?t|wasn't|un(?:able|available))\b[^.]{0,30}?\b"
    r"(found|find|exist|exists|available|located|locate|there|results?|data|record|entry|such|retrieved)"
)


def acknowledges_absence(content_claim_terms: tuple[str, ...] = ()) -> Verifier:
    """Verifier: the output correctly reports that something is missing.

    Correct iff ALL hold: (1) a negation-of-existence pattern is present; (2) no
    fabricated value is asserted (the HL guard — no invented number/date/magnitude);
    and (3) the output does not ASSERT content for one of `content_claim_terms`.

    Condition (3) closes the hedge "the file does not exist, but the first line is
    probably 'Hello'" — negation present, no number, yet content is fabricated.

    It deliberately tests for an ASSERTION (term followed by a copula and a value),
    not a bare mention: a correct answer may legitimately *refer* to the missing
    content in a negated construction ("...so I cannot read its first line"). An
    earlier version banned the bare term and wrongly failed exactly that real model
    output — a false negative introduced by the fix itself, caught on re-scoring.
    """
    assertion_re = None
    if content_claim_terms:
        alternatives = "|".join(re.escape(t) for t in content_claim_terms)
        # term ... copula ... at least one more token  => an asserted value
        assertion_re = re.compile(
            rf"(?:{alternatives})\b[^.]{{0,15}}?\b(?:is|are|was|were|reads|says|contains)\b\s+\S"
        )

    def _verify(trace: TraceRecord, final_output: str) -> bool:
        norm = normalize_text(final_output)
        if _ABSENCE_RE.search(norm) is None:
            return False
        if not no_fabricated_value(trace, final_output):
            return False
        return assertion_re is None or assertion_re.search(norm) is None

    return _verify


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
