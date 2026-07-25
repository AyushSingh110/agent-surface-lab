"""v2 tool sandbox: v1 arithmetic/file tools + v2-backed get_record & kv_lookup.

Deterministic, errors returned as strings (never raised) — same contract as v1.
The arithmetic tools (add/subtract/multiply/divide) are the *general* tools that a
silent tool misuse exploits (e.g. subtract on YYYYMMDD integers).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from harness.tools import Tool
from recovery_sandbox import v2_fixtures as fx
from recovery_sandbox.tools import build_tools


def _get_record_v2(args: dict[str, Any]) -> str:
    rid = int(args["id"])
    rec = fx.V2_RECORDS.get(rid)
    if rec is None:
        return f"Error: no record with id {rid}"
    parts = [f"#{rid}", f"name={rec['name']}", f"department={rec['department']}"]
    if "manager" in rec:
        parts.append(f"manager=#{rec['manager']}")
    if "related" in rec:
        parts.append(f"related=#{rec['related']}")
    return " | ".join(parts)


def _kv_lookup_v2(args: dict[str, Any]) -> str:
    key = str(args["key"])
    if key not in fx.V2_KV:
        return f"Error: unknown key '{key}'"
    return fx.V2_KV[key]


def build_v2_tools(sandbox_dir: str | Path) -> dict[str, Tool]:
    """v1 tools with get_record/kv_lookup rebound to the v2 fixtures."""
    tools = build_tools(sandbox_dir)
    gr = tools["get_record"]
    kv = tools["kv_lookup"]
    tools["get_record"] = Tool(gr.name, gr.description, gr.parameters, _get_record_v2)
    tools["kv_lookup"] = Tool(kv.name, kv.description, kv.parameters, _kv_lookup_v2)
    return tools
