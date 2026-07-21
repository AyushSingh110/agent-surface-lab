"""Shared test fixtures: a recorded 2-step arithmetic trace built via the runner.

Building the trace through the real runner (with a scripted FakeBackend) rather than
by hand is deliberate: it means the reconstruct test validates against snapshots
produced by the actual recording path, not against hand-written expectations.
"""
from __future__ import annotations

import pytest

from harness.backend import ChatResponse, FakeBackend
from harness.config import Config
from harness.recorder import build_trace, now_iso
from harness.runner import run_agent
from harness.tools import ARITHMETIC_TOOLS, ToolRegistry
from harness.trace import TraceRecord


@pytest.fixture
def arithmetic_registry() -> ToolRegistry:
    return ToolRegistry(list(ARITHMETIC_TOOLS))


@pytest.fixture
def recorded_trace(arithmetic_registry: ToolRegistry) -> TraceRecord:
    """A recorded run of '(3+4)*5': add(3,4) -> multiply(7,5) -> final '35'."""
    config = Config(temperature=0.0, n_replays=3, max_turns=8)
    script = [
        ChatResponse(content="", tool_name="add", tool_args={"a": 3, "b": 4}),
        ChatResponse(content="", tool_name="multiply", tool_args={"a": 7, "b": 5}),
        ChatResponse(content="The answer is 35.", tool_name=None, tool_args=None),
    ]
    backend = FakeBackend(script, model_tag="fake-model")
    system_prompt = "You are a calculator agent. Use the tools."
    initial_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Compute (3 + 4) * 5."},
    ]
    result = run_agent(
        initial_messages=initial_messages,
        tools=arithmetic_registry,
        backend=backend,
        config=config,
    )
    trace = build_trace(
        trace_id="t-arith-0",
        task="Compute (3 + 4) * 5.",
        task_class="arithmetic",
        system_prompt=system_prompt,
        initial_messages=initial_messages,
        steps=result.steps,
        final_output=result.final_output,
        model_tag=backend.model_tag,
        seed=config.seed,
        temperature=config.temperature,
        ts_start=now_iso(),
        requirement="Return the numeric result.",
    )
    # Stash the backend so a test can cross-check what the model actually saw.
    trace._seen_contexts = backend.seen_contexts  # type: ignore[attr-defined]
    return trace
