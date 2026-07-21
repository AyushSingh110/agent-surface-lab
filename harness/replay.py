"""Counterfactual replay: reconstruct context up to step k, intervene, resume.

`reconstruct` is the load-bearing function: it must recreate the *exact* prompt
the model saw entering step k. It does so purely from `initial_messages` and
`messages_appended_by` over the prior steps — the same growth function the runner
used — so a reconstructed context equals the recorded `context_snapshot` by
construction. `tests/test_replay.py` verifies that equality on a real recorded run.

`replay_cell` runs N replays of one (intervention, trace) and returns the per-replay
success booleans (via a deterministic verifier). Reporting the DISTRIBUTION over N,
not a single sample, is the §8-item-10 decision.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Callable

from harness.backend import ChatBackend
from harness.config import Config
from harness.runner import RunResult, run_agent
from harness.tools import ToolRegistry
from harness.trace import Message, TraceRecord, messages_appended_by

# A deterministic verifier maps (trace, final_output) -> did the run succeed?
# NEVER an LLM judge (CLAUDE.md / §8 item 4): must be a deterministic check.
Verifier = Callable[[TraceRecord, str], bool]


@dataclass
class InterventionOutcome:
    """What an intervention produces: the context to resume from and where.

    Defined here (not in interventions.py) so replay does not depend on the concrete
    interventions — interventions depend on replay, never the reverse.

    Attributes:
        resume_messages: The (possibly edited/rewound) context to resume the agent from.
        resume_turn: The step index to resume numbering/budget at (a rollback lowers it).
        name: Intervention name, recorded on the outcome.
        note: Short human-readable description of what was changed.
    """

    resume_messages: list[Message]
    resume_turn: int
    name: str
    note: str


# An intervention edits/rewinds a trace at step k and says where to resume.
Intervention = Callable[[TraceRecord, int, Config], InterventionOutcome]


def reconstruct(trace: TraceRecord, k: int) -> list[Message]:
    """Rebuild the exact message context the model saw entering step k.

    Args:
        trace: The recorded run.
        k: Step index in [0, len(steps)]. k=0 is the initial context; k=len(steps)
            is the full context after the last step.

    Returns:
        A fresh message list (deep-copied) identical to what the runner had entering
        step k. For k < len(steps) this equals trace.steps[k].context_snapshot.

    Raises:
        IndexError: if k is out of range.
    """
    if not 0 <= k <= len(trace.steps):
        raise IndexError(f"k={k} out of range for trace with {len(trace.steps)} steps")
    messages = copy.deepcopy(trace.initial_messages)
    for i in range(k):
        messages.extend(messages_appended_by(trace.steps[i]))
    return messages


def replay_once(
    *,
    trace: TraceRecord,
    resume_messages: list[Message],
    resume_turn: int,
    tools: ToolRegistry,
    backend: ChatBackend,
    config: Config,
    replay_index: int,
) -> RunResult:
    """Resume the agent forward from an (already intervened) context.

    The turn cap is on TOTAL turns, so remaining budget is `max_turns - resume_turn`;
    a rollback (smaller resume_turn) therefore gets more budget, and a late failure
    correctly gets little — matching real deployment economics.
    """
    remaining = config.max_turns
    return run_agent(
        initial_messages=resume_messages,
        tools=tools,
        backend=backend,
        config=config,
        replay_index=replay_index,
        start_turn=resume_turn,
        max_turns=remaining,
    )


def replay_cell(
    *,
    trace: TraceRecord,
    k: int,
    intervention: Intervention,
    tools: ToolRegistry,
    backend: ChatBackend,
    config: Config,
    verifier: Verifier,
    n: int | None = None,
) -> list[bool]:
    """Run N replays of one (intervention, trace) and return per-replay success.

    Args:
        trace: The failing trace to attempt to recover.
        k: The oracle-labeled failure step to intervene at.
        intervention: The intervention to apply at k (returns a resume context).
        tools, backend, config: Sandbox, model, run config.
        verifier: Deterministic success check on the replayed final output.
        n: Number of replays; defaults to config.n_replays. Must be >= 1.

    Returns:
        A list of length n of success booleans — the recovery DISTRIBUTION for this
        cell (not collapsed to a single number here; the metrics layer aggregates).
    """
    n_eff = config.n_replays if n is None else n
    if n_eff < 1:
        raise ValueError(f"n must be >= 1, got {n_eff}")
    outcomes: list[bool] = []
    for replay_index in range(n_eff):
        plan = intervention(trace, k, config)
        result = replay_once(
            trace=trace,
            resume_messages=plan.resume_messages,
            resume_turn=plan.resume_turn,
            tools=tools,
            backend=backend,
            config=config,
            replay_index=replay_index,
        )
        outcomes.append(verifier(trace, result.final_output))
    return outcomes
