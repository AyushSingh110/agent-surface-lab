"""Deterministic sandbox tools for the kill test.

Built on `harness.tools.Tool`. File tools are bound to a per-run sandbox directory
so each run's writes are isolated (and so `file_written` can check the same dir).
Every tool is a pure function of its args plus the fixed fixtures / the sandbox dir;
tool ERRORS are returned as strings (agent-observable data — the substrate of
`tool_misuse`), never raised, so the run and its trace survive.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from harness.tools import Tool
from harness.verifiers import normalize_text
from recovery_sandbox import fixtures as fx

_NUM_PAIR = {
    "type": "object",
    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
    "required": ["a", "b"],
}


def _add(args: dict[str, Any]) -> str:
    return str(float(args["a"]) + float(args["b"]))


def _subtract(args: dict[str, Any]) -> str:
    return str(float(args["a"]) - float(args["b"]))


def _multiply(args: dict[str, Any]) -> str:
    return str(float(args["a"]) * float(args["b"]))


def _divide(args: dict[str, Any]) -> str:
    b = float(args["b"])
    if b == 0:
        # The tool_misuse bait: an explicit, observable error the agent must handle.
        return "Error: division by zero is undefined"
    return str(float(args["a"]) / b)


def _search(args: dict[str, Any]) -> str:
    return fx.SEARCH_CORPUS.get(normalize_text(str(args["query"])), fx.NO_RESULTS)


def _kv_lookup(args: dict[str, Any]) -> str:
    key = str(args["key"])
    if key not in fx.KV_STORE:
        return f"Error: unknown key '{key}'"
    return fx.KV_STORE[key]


def _get_record(args: dict[str, Any]) -> str:
    rid = int(args["id"])
    rec = fx.RECORDS.get(rid)
    if rec is None:
        return f"Error: no record with id {rid}"
    parts = [f"#{rid}", f"name={rec['name']}", f"department={rec['department']}"]
    if "manager" in rec:
        parts.append(f"manager=#{rec['manager']}")
    if "related" in rec:
        parts.append(f"related=#{rec['related']}")  # drift bait only
    return " | ".join(parts)


def _unit_convert(args: dict[str, Any]) -> str:
    value = float(args["value"])
    src = str(args["from"]).strip().lower()
    dst = str(args["to"]).strip().lower()
    if src not in fx.SUPPORTED_UNITS or dst not in fx.SUPPORTED_UNITS:
        return f"Error: unsupported unit conversion {src!r}->{dst!r} (supported: c, f, k)"
    celsius = {"c": value, "f": (value - 32.0) * 5.0 / 9.0, "k": value - 273.15}[src]
    result = {"c": celsius, "f": celsius * 9.0 / 5.0 + 32.0, "k": celsius + 273.15}[dst]
    return str(round(result, 4))


def build_tools(sandbox_dir: str | Path) -> dict[str, Tool]:
    """Construct all sandbox tools, binding file tools to `sandbox_dir`.

    Args:
        sandbox_dir: A per-run writable directory. Created if absent.

    Returns:
        Mapping of tool name -> Tool, deterministic given the fixtures and this dir.
    """
    base = Path(sandbox_dir)
    base.mkdir(parents=True, exist_ok=True)

    def _write_file(args: dict[str, Any]) -> str:
        # Confine writes to the sandbox: reject path escapes rather than following them.
        rel = Path(str(args["path"]))
        if rel.is_absolute() or ".." in rel.parts:
            return f"Error: path '{rel}' must be relative to the sandbox"
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(args["content"]), encoding="utf-8")
        return "ok"

    def _read_file(args: dict[str, Any]) -> str:
        name = str(args["path"])
        if name in fx.READ_ONLY_FILES:  # canned corpus (e.g. log.txt) takes precedence
            return fx.READ_ONLY_FILES[name]
        target = base / name
        if not target.is_file():
            return f"Error: file not found: {name}"
        return target.read_text(encoding="utf-8")

    tools = [
        Tool("add", "Add two numbers and return their sum.", _NUM_PAIR, _add),
        Tool("subtract", "Subtract b from a and return the difference.", _NUM_PAIR, _subtract),
        Tool("multiply", "Multiply two numbers and return their product.", _NUM_PAIR, _multiply),
        Tool("divide", "Divide a by b. Errors if b is zero.", _NUM_PAIR, _divide),
        Tool(
            "search",
            "Search a small knowledge base; returns a snippet or 'No results found.'",
            {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            _search,
        ),
        Tool(
            "kv_lookup",
            "Look up a key in the fact store; errors on an unknown key.",
            {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]},
            _kv_lookup,
        ),
        Tool(
            "get_record",
            "Fetch an employee record by integer id; errors if the id is unknown.",
            {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
            _get_record,
        ),
        Tool(
            "unit_convert",
            "Convert a temperature between c, f, k. Errors on unsupported units.",
            {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                },
                "required": ["value", "from", "to"],
            },
            _unit_convert,
        ),
        Tool(
            "write_file",
            "Write content to a file inside the sandbox; returns 'ok'.",
            {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
            _write_file,
        ),
        Tool(
            "read_file",
            "Read a file's content; errors if the file is absent.",
            {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            _read_file,
        ),
    ]
    return {t.name: t for t in tools}
