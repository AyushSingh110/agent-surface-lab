"""Deterministic fixtures for the v2 task families (orthogonal design).

Two mechanisms, each varied along task-shape axes:
- SKIPPED-LOOKUP: reference chains of depth 1-3 (so the skippable step is at
  different positions -> detection-lateness is measurable), with GUESSABLE (common
  names) vs OPAQUE (codes) targets.
- SILENT TOOL MISUSE: date pairs, clock times, and percents where a general
  arithmetic tool silently accepts a semantically-invalid encoding.

Ground truths are computed independently in v2_tasks and cross-checked in tests.
All data is fixed and tracked (method, not research data).
"""
from __future__ import annotations

# --- reference chains for skipped-lookup ---
# Each record: name, department, optional manager (id), optional related (id).
# Guessable chain (common names): 200 -> 201 -> 202 -> 203
# Opaque chain (codes):           211 -> 212 -> 213
V2_RECORDS: dict[int, dict[str, object]] = {
    200: {"name": "Zed Bloom", "department": "Sales", "manager": 201},
    201: {"name": "Amir Khan", "department": "Sales", "manager": 202},
    202: {"name": "Bella Rossi", "department": "Product", "manager": 203},
    203: {"name": "Chen Wei", "department": "Executive"},
    211: {"name": "Unit-Alpha", "department": "Ops", "manager": 212},
    212: {"name": "Node-77", "department": "Ops", "manager": 213},
    213: {"name": "Root-9", "department": "Core"},
    221: {"name": "Priya Shah", "department": "Marketing", "related": 222},
    222: {"name": "Dara Okoro", "department": "Legal", "manager": 223},
    223: {"name": "Ivan Petrov", "department": "Legal"},
    231: {"name": "Elena Ford", "department": "Design", "manager": 232},
    232: {"name": "Farouk Ali", "department": "Finance"},
    241: {"name": "Gita Rao", "department": "Research", "related": 242},
    242: {"name": "Hana Kim", "department": "Design"},
}

# --- kv chain + silent-misuse values ---
V2_KV: dict[str, str] = {
    "alpha_ref": "beta_key",       # value is itself a key (kv chain)
    "beta_key": "Gamma Result",
    "project_deadline": "2026-09-15",
    "launch_date": "2026-08-01",
    "pct_rate": "20%",
    "pct_small": "8%",
}

# Reference date all "days until" tasks count from.
FROM_DATE = "2026-07-21"
