"""Trace data model + the single source of truth for how a step grows context.

A *trace* is one agent run on one task. Each *step* records the exact messages
the model saw (``context_snapshot``), its output, any tool call/result, and
timing. Storing the snapshot per step is what lets `replay.reconstruct` be
verified against ground truth (design lesson from the DoVer read): replay must be
able to recreate the exact prompt the model actually saw, not an approximation.

`messages_appended_by` is the ONE function that defines how a completed step
extends the running message list. Both the runner (forward) and the replay layer
(reconstruct) call it, so they cannot drift apart — that shared definition is
what makes reconstruction provably exact.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

# A chat message in Ollama's format: {"role", "content", optional "tool_calls"/"name"}.
Message = dict[str, Any]


@dataclass
class StepRecord:
    """One agent step.

    Attributes:
        turn: Monotonic 0-based step index.
        context_snapshot: The exact message list passed to the model this step.
            This is the ground truth `reconstruct` is validated against.
        llm_output: The model's raw text output this step (may be empty if it only
            emitted a tool call).
        tool_name: Name of the tool called this step, or None for a final answer.
        tool_args: Arguments passed to the tool, or None.
        tool_result: The tool's returned value as a string, or None.
        latency_ms: Wall-clock latency of the model call.
        token_count: Prompt+completion token count reported by the backend, if any.
        ts: ISO-8601 timestamp of the step (per-step timestamp, CLAUDE.md §4).
    """

    turn: int
    context_snapshot: list[Message]
    llm_output: str
    tool_name: Optional[str]
    tool_args: Optional[dict[str, Any]]
    tool_result: Optional[str]
    latency_ms: float
    token_count: int
    ts: str

    @property
    def called_tool(self) -> bool:
        """True if this step invoked a tool (rather than producing a final answer)."""
        return self.tool_name is not None


@dataclass
class TraceRecord:
    """One recorded agent run.

    Ground-truth and oracle-label fields (`answer_correct`, `failure_class`,
    `failure_step_k`) are filled in *after* the run — by the deterministic verifier
    and the human labeling pass respectively — and default to None at record time so
    we never confuse "not yet labeled" with a real value (CLAUDE.md §3: no fabricated
    results).
    """

    trace_id: str
    task: str
    task_class: str
    system_prompt: str
    initial_messages: list[Message]
    steps: list[StepRecord]
    final_output: str
    # Reproducibility metadata (logged on every trace).
    model_tag: str
    seed: int
    temperature: float
    ts_start: str
    # Filled in post-hoc; None means "not determined", never a guessed value.
    answer_correct: Optional[bool] = None
    failure_class: Optional[str] = None
    failure_step_k: Optional[int] = None
    requirement: Optional[str] = None  # the task's explicit requirement (for injection intervention)

    def to_json_line(self) -> str:
        """Serialize to a single JSONL line."""
        return json.dumps(asdict(self), ensure_ascii=False)

    @staticmethod
    def from_json_line(line: str) -> "TraceRecord":
        """Deserialize a JSONL line back into a TraceRecord (steps included)."""
        raw = json.loads(line)
        steps = [StepRecord(**s) for s in raw.pop("steps")]
        return TraceRecord(steps=steps, **raw)


def messages_appended_by(step: StepRecord) -> list[Message]:
    """Return the messages a completed step appends to the running context.

    This is the single definition of "what a step adds": the assistant message
    (carrying the model's output and, if present, the tool call) followed by the
    tool-result message when a tool was called. The runner uses it to grow context
    forward; `replay.reconstruct` uses it to rebuild context up to step k. Keeping
    both on this one function is precisely what guarantees reconstruction is exact.

    Args:
        step: A completed StepRecord.

    Returns:
        The list of messages appended after this step ran.
    """
    assistant: Message = {"role": "assistant", "content": step.llm_output}
    if step.called_tool:
        # Mirror the tool_call shape the backend emits so a reconstructed context
        # is byte-identical to what the live run appended.
        assistant["tool_calls"] = [
            {"function": {"name": step.tool_name, "arguments": step.tool_args or {}}}
        ]
        tool_msg: Message = {
            "role": "tool",
            "name": step.tool_name,
            "content": "" if step.tool_result is None else step.tool_result,
        }
        return [assistant, tool_msg]
    return [assistant]
