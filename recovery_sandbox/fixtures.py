"""Deterministic fixtures backing the sandbox tools.

Every ground-truth answer in `docs/kill-test-tasks.md` must be checkable against
these tables — that is the whole point of committing them as code (they are method,
not research data, so they are tracked, not under `data/`). Nothing here is random;
the same query/id/key always returns the same value.

Consistency invariants (asserted in `tests/test_sandbox.py`):
- among records #1..#6, exactly 2 are in "Sales"        (CO-4 GT = 2)
- among records #1..#10, exactly 5 distinct departments (GM-3 GT = the 5 names)
- record #204's department is "Logistics"               (DR-1)
- record #150's manager is #77, whose name is "Priya Nair" (DR-4)
- `log.txt` has 10 lines, exactly 3 containing "ERROR"  (CO-2 GT = 3)
"""
from __future__ import annotations

# --- get_record table -------------------------------------------------------
# Each record: name, department, optional manager id, optional "related" hook
# (the hook exists only to bait prompt_drift; it is never part of any ground truth).
RECORDS: dict[int, dict[str, object]] = {
    1: {"name": "Alice Chen", "department": "Sales"},
    2: {"name": "Ben Ortiz", "department": "Engineering"},
    3: {"name": "Carla Diop", "department": "Marketing"},
    4: {"name": "Deepak Rao", "department": "Sales"},
    5: {"name": "Elena Petrov", "department": "Finance"},
    6: {"name": "Farid Hassan", "department": "Engineering"},
    7: {"name": "Grace Kim", "department": "Marketing"},
    8: {"name": "Hiro Tanaka", "department": "Logistics"},
    9: {"name": "Ingrid Larsen", "department": "Finance"},
    10: {"name": "Jamal Wright", "department": "Engineering"},
    77: {"name": "Priya Nair", "department": "Operations"},
    99: {"name": "Quentin Blake", "department": "Research"},
    150: {"name": "Kofi Mensah", "department": "Product", "manager": 77},
    204: {"name": "Lena Vogt", "department": "Logistics", "related": 99},
}

# --- search corpus ----------------------------------------------------------
# Keys are the NORMALIZED query (see harness.verifiers._normalize semantics:
# lowercased, whitespace/commas collapsed). Unknown queries return NO_RESULTS.
SEARCH_CORPUS: dict[str, str] = {
    "capital of australia": "Canberra is the capital of Australia.",
    "boiling point of water": "Water boils at 100 degrees Celsius at sea level.",
}
NO_RESULTS = "No results found."

# --- key/value fact store ---------------------------------------------------
KV_STORE: dict[str, str] = {
    "project_x_deadline": "2026-09-15",
    "greeting_fr": "bonjour",
}

# --- read-only file corpus (served by read_file before the writable sandbox) --
# log.txt: 10 lines, exactly 3 contain "ERROR" (CO-2 GT = 3).
_LOG_TXT = "\n".join(
    [
        "INFO service started",
        "ERROR disk read failed",
        "INFO cache warm",
        "WARN latency high",
        "ERROR network timeout",
        "INFO request handled",
        "INFO request handled",
        "ERROR db connection lost",
        "WARN retry scheduled",
        "INFO shutdown clean",
    ]
)
READ_ONLY_FILES: dict[str, str] = {"log.txt": _LOG_TXT}

# --- unit_convert whitelist -------------------------------------------------
# Only these units are supported; anything else (e.g. "fathom") is an error,
# which is the intended tool_misuse bait for TM-2.
SUPPORTED_UNITS: frozenset[str] = frozenset({"c", "f", "k"})
