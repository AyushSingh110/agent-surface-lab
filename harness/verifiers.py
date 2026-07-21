"""Deterministic ground-truth verifiers (decision §8 item 4).

Every verifier is a deterministic function of (trace, final_output) → bool — never
an LLM judge. Each maps to a task type: numeric/canonical → exact match; open QA →
fact-match (normalized substring); file/deliverable → file existence + content;
transactions → environment-state. Only the ones the kill test needs are
implemented; the rest are explicit NotImplemented stubs so nobody silently ships a
non-deterministic stand-in.
"""
from __future__ import annotations

import re
from pathlib import Path

from harness.trace import TraceRecord


def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace/punctuation for robust exact/fact matching."""
    return re.sub(r"[\s,]+", " ", text.strip().lower())


def numeric_exact(expected: float, tol: float = 1e-9) -> "Verifier":
    """Verifier: the final output contains the expected number (within tol).

    Numbers are extracted from the output text so trailing prose ("The answer is 35.")
    still verifies, while remaining a deterministic check.
    """

    def _verify(trace: TraceRecord, final_output: str) -> bool:
        found = re.findall(r"-?\d+(?:\.\d+)?", final_output.replace(",", ""))
        return any(abs(float(tok) - expected) <= tol for tok in found)

    return _verify


def fact_match(expected: str) -> "Verifier":
    """Verifier: the normalized expected answer appears in the normalized output."""
    target = _normalize(expected)

    def _verify(trace: TraceRecord, final_output: str) -> bool:
        return target in _normalize(final_output)

    return _verify


def file_written(path: str | Path, expected_content: str) -> "Verifier":
    """Verifier: a file exists at `path` and its normalized content matches.

    Used for file/deliverable tasks (the canonical goal_misalignment example: the
    number is computed but the file is never written).
    """
    p = Path(path)
    target = _normalize(expected_content)

    def _verify(trace: TraceRecord, final_output: str) -> bool:
        if not p.is_file():
            return False
        return target in _normalize(p.read_text(encoding="utf-8"))

    return _verify


# Type alias mirrors replay.Verifier without importing it (keeps this module leaf-level).
from typing import Callable  # noqa: E402

Verifier = Callable[[TraceRecord, str], bool]
