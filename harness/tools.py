"""Tool sandbox: deterministic instrumented tools + a registry.

Tools are pure and deterministic so that any nondeterminism in a trace comes from
the model, never the environment — a precondition for a clean counterfactual
(the tool result for the same args must be identical on replay). Each tool
carries its own JSON schema so the registry can hand the backend a tools list.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

# A tool implementation maps validated args to a string result.
ToolFn = Callable[[dict[str, Any]], str]


@dataclass(frozen=True)
class Tool:
    """A registered tool: its name, JSON schema, and deterministic implementation."""

    name: str
    description: str
    parameters: dict[str, Any]
    fn: ToolFn

    def schema(self) -> dict[str, Any]:
        """The tool in the function-calling schema the backend expects."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Holds the tools available in a run and executes calls against them."""

    def __init__(self, tools: list[Tool]) -> None:
        names = [t.name for t in tools]
        if len(names) != len(set(names)):
            raise ValueError(f"duplicate tool names in registry: {names}")
        self._tools = {t.name: t for t in tools}

    def schemas(self) -> list[dict[str, Any]]:
        """Schemas for all tools, to pass to the backend."""
        return [t.schema() for t in self._tools.values()]

    def execute(self, name: str, args: dict[str, Any]) -> str:
        """Execute a tool call, returning a string result.

        An unknown tool or a bad-argument error is returned as an explicit error
        STRING (not raised): a tool error is legitimate agent-observable data (it is
        exactly how `tool_misuse` failures manifest) and must be recorded in the
        trace, not swallowed or crashed on. Registry-level programming errors (e.g.
        None args) still raise.
        """
        if args is None:
            raise ValueError(f"tool '{name}' called with args=None (harness bug, not a model error)")
        tool = self._tools.get(name)
        if tool is None:
            return f"Error: unknown tool '{name}'"
        try:
            return tool.fn(args)
        except (KeyError, TypeError, ValueError) as exc:
            # Surface the bad call as an observable tool error, preserving the run.
            return f"Error: {name} could not run with args {args}: {exc}"


# --- A minimal deterministic tool set for the kill test's arithmetic tasks. ---
# (The kill-test task suite is the human's to design; these exist so the runner
# and its tests have real, deterministic tools to exercise.)

def _add(args: dict[str, Any]) -> str:
    return str(float(args["a"]) + float(args["b"]))


def _multiply(args: dict[str, Any]) -> str:
    return str(float(args["a"]) * float(args["b"]))


_NUM_PAIR = {
    "type": "object",
    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
    "required": ["a", "b"],
}

ARITHMETIC_TOOLS = [
    Tool("add", "Add two numbers and return their sum.", _NUM_PAIR, _add),
    Tool("multiply", "Multiply two numbers and return their product.", _NUM_PAIR, _multiply),
]
