"""The intervention arms of the recovery matrix.

Each intervention takes (trace, k, config) and returns an InterventionOutcome:
the context to resume from and the turn to resume at. They are pure planners —
they compute a resume context but do not run the model; `replay.replay_cell`
does the resuming. This keeps them trivially testable.

`no_op` is deliberately first and first-class: it is the control arm that re-runs
from k with NO change, telling us which runs would have self-recovered. The
iatrogenic rate — the study's central contribution post-DoVer — is defined
against it, so it must never be dropped for compute (work-plan §2 reframe).
"""
from __future__ import annotations

from harness.config import Config
from harness.replay import Intervention, InterventionOutcome, reconstruct
from harness.trace import TraceRecord

_REFLECT_PROMPT = (
    "Before continuing, critically review your work so far for mistakes. "
    "If you find an error, correct it, then complete the task."
)


def no_op(trace: TraceRecord, k: int, config: Config) -> InterventionOutcome:
    """Control: resume from k with no modification (does the run self-recover?)."""
    return InterventionOutcome(
        resume_messages=reconstruct(trace, k),
        resume_turn=k,
        name="no_op",
        note="resume from k unchanged (control arm for iatrogenic rate)",
    )


def reflect_and_retry(trace: TraceRecord, k: int, config: Config) -> InterventionOutcome:
    """The incumbent under trial: inject a self-critique prompt at k, then resume."""
    messages = reconstruct(trace, k)
    messages.append({"role": "user", "content": _REFLECT_PROMPT})
    return InterventionOutcome(
        resume_messages=messages,
        resume_turn=k,
        name="reflect_and_retry",
        note="injected self-critique prompt at k",
    )


def rollback_n(n: int) -> Intervention:
    """Factory for a rollback intervention that rewinds n steps and resumes.

    Rewinding below step 0 is clamped to 0 (restart from the initial context),
    which is a legitimate — if blunt — recovery move.

    Args:
        n: Number of steps to rewind (n>=1).

    Returns:
        An Intervention closure.
    """
    if n < 1:
        raise ValueError(f"rollback n must be >= 1, got {n}")

    def _rollback(trace: TraceRecord, k: int, config: Config) -> InterventionOutcome:
        j = max(0, k - n)
        return InterventionOutcome(
            resume_messages=reconstruct(trace, j),
            resume_turn=j,
            name=f"rollback_{n}",
            note=f"rewound from step {k} to step {j}",
        )

    return _rollback


def requirement_injection(trace: TraceRecord, k: int, config: Config) -> InterventionOutcome:
    """Hand the agent the explicit requirement it missed, at k, then resume.

    Fails loudly if the trace carries no `requirement`: injecting a missing
    requirement we don't have would mean fabricating one, which would corrupt the
    result (CLAUDE.md §3). The task set must supply requirements for this arm.
    """
    if trace.requirement is None:
        raise ValueError(
            f"trace {trace.trace_id} has no `requirement`; cannot run requirement_injection"
        )
    messages = reconstruct(trace, k)
    messages.append(
        {"role": "user", "content": f"You must satisfy this requirement: {trace.requirement}"}
    )
    return InterventionOutcome(
        resume_messages=messages,
        resume_turn=k,
        name="requirement_injection",
        note="injected the missing requirement at k",
    )


# The kill-test arm set (work-plan §8 item 3), no_op first as the control.
KILL_TEST_INTERVENTIONS: dict[str, Intervention] = {
    "no_op": no_op,
    "reflect_and_retry": reflect_and_retry,
    "rollback_2": rollback_n(2),
    "requirement_injection": requirement_injection,
}
