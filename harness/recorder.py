"""Trace persistence: assemble a TraceRecord and read/write JSONL.

Persistence choice: one JSONL line per *trace* (steps nested), not one line per
step. A recovery study needs a whole trace as a unit (reconstruct context up to k,
then replay), and trace-level metadata (seed, model, ground truth, oracle labels)
must travel with its steps. One-trace-per-line keeps that unit intact while staying
append-only and stream-readable (CLAUDE.md §4/§5). Raw traces live under `data/`
(gitignored).

StepRecords are constructed in exactly one place — the runner — so context growth
(`messages_appended_by`) and what gets stored can never diverge. This module only
packages already-built steps and does I/O.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from harness.trace import Message, StepRecord, TraceRecord


def now_iso() -> str:
    """UTC timestamp in ISO-8601 (used for per-step and per-trace timestamps)."""
    return datetime.now(timezone.utc).isoformat()


def build_trace(
    *,
    trace_id: str,
    task: str,
    task_class: str,
    system_prompt: str,
    initial_messages: list[Message],
    steps: list[StepRecord],
    final_output: str,
    model_tag: str,
    seed: int,
    temperature: float,
    ts_start: str,
    requirement: Optional[str] = None,
) -> TraceRecord:
    """Package runner output into a TraceRecord (no ground truth / labels yet).

    Ground-truth (`answer_correct`) and oracle labels (`failure_class`,
    `failure_step_k`) are deliberately left None here; they are set later by the
    deterministic verifier and the human labeling pass, so an unlabeled trace can
    never be mistaken for a labeled one (CLAUDE.md §3).
    """
    return TraceRecord(
        trace_id=trace_id,
        task=task,
        task_class=task_class,
        system_prompt=system_prompt,
        initial_messages=initial_messages,
        steps=steps,
        final_output=final_output,
        model_tag=model_tag,
        seed=seed,
        temperature=temperature,
        ts_start=ts_start,
        requirement=requirement,
    )


def append_trace(trace: TraceRecord, path: str | Path) -> None:
    """Append one trace as a JSONL line, creating the parent dir if needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(trace.to_json_line() + "\n")


def load_traces(path: str | Path) -> list[TraceRecord]:
    """Load all traces from a JSONL file. Fails loudly if the file is missing."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"trace file not found: {p}")
    with p.open("r", encoding="utf-8") as fh:
        return [TraceRecord.from_json_line(line) for line in fh if line.strip()]
