"""Agent runner: a minimal ReAct-style loop, resumable for replay.

One agent step = one model call and at most one tool execution. The runner is the
single place StepRecords are built, and it grows the running context with
`messages_appended_by` — the same function `replay.reconstruct` uses — so a
recorded context and a reconstructed one are exact by construction.

The loop is `run_agent`; both fresh generation and forward-resume during replay
call it. `start_turn` lets replay continue numbering steps after a reconstructed
prefix.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from time import perf_counter
from typing import Optional

from harness.backend import ChatBackend
from harness.config import Config
from harness.recorder import now_iso
from harness.tools import ToolRegistry
from harness.trace import Message, StepRecord, messages_appended_by


@dataclass
class RunResult:
    """Outcome of an agent run (fresh or resumed).

    Attributes:
        final_output: The agent's final text answer (last content emitted).
        steps: StepRecords produced during this run segment.
        messages: The full running context at the end (initial + all appends).
        stopped_reason: "final" (agent answered) or "max_turns" (hit the cap).
    """

    final_output: str
    steps: list[StepRecord]
    messages: list[Message]
    stopped_reason: str


def run_agent(
    *,
    initial_messages: list[Message],
    tools: ToolRegistry,
    backend: ChatBackend,
    config: Config,
    replay_index: int = 0,
    start_turn: int = 0,
    max_turns: Optional[int] = None,
) -> RunResult:
    """Run the agent loop from `initial_messages` until it answers or hits the cap.

    Args:
        initial_messages: The starting context (system+user for a fresh run, or a
            reconstructed+intervened context for a replay). It is deep-copied so the
            caller's list is never mutated.
        tools: The tool sandbox for this run.
        backend: Injected chat backend (real Ollama or a test fake).
        config: Run configuration (seed, temperature, max_turns).
        replay_index: Which replay in a cell this is; offsets the seed so the N
            replays are distinct-but-reproducible draws.
        start_turn: Step index to number the first step of this segment with.
        max_turns: Overrides config.max_turns if given (the cap is on TOTAL turns,
            so a resumed run passes remaining budget via this argument).

    Returns:
        A RunResult. On an empty/looping run that never answers, stopped_reason is
        "max_turns" and final_output is the last content seen (possibly "").
    """
    messages = copy.deepcopy(initial_messages)
    steps: list[StepRecord] = []
    limit = config.max_turns if max_turns is None else max_turns
    schemas = tools.schemas()

    turn = start_turn
    while turn < limit:
        snapshot = copy.deepcopy(messages)  # exactly what the model sees this step
        t0 = perf_counter()
        resp = backend.chat(messages, schemas, config.sampling_options(replay_index))
        latency_ms = (perf_counter() - t0) * 1000.0

        if resp.tool_name is None:
            # Final answer: record the step, append the assistant message, stop.
            steps.append(
                StepRecord(
                    turn=turn,
                    context_snapshot=snapshot,
                    llm_output=resp.content,
                    tool_name=None,
                    tool_args=None,
                    tool_result=None,
                    latency_ms=latency_ms,
                    token_count=resp.token_count,
                    ts=now_iso(),
                )
            )
            messages.append({"role": "assistant", "content": resp.content})
            return RunResult(resp.content, steps, messages, "final")

        tool_result = tools.execute(resp.tool_name, resp.tool_args or {})
        step = StepRecord(
            turn=turn,
            context_snapshot=snapshot,
            llm_output=resp.content,
            tool_name=resp.tool_name,
            tool_args=resp.tool_args,
            tool_result=tool_result,
            latency_ms=latency_ms,
            token_count=resp.token_count,
            ts=now_iso(),
        )
        steps.append(step)
        messages.extend(messages_appended_by(step))
        turn += 1

    # Hit the turn cap without a final answer — a legitimate failure outcome.
    final = steps[-1].llm_output if steps else ""
    return RunResult(final, steps, messages, "max_turns")
