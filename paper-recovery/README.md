# paper-recovery (Ideas A + B)

**Spine (post-DoVer reframe):** *not all repair helps — which intervention recovers which
failure class, and where standard self-correction actively harms.* The **iatrogenic rate**
(interventions that do worse than doing nothing) is the central contribution, measured causally
by counterfactual replay against a **no-op control**. See `docs/work-plan.md` §2 and
`docs/literature-review.md` (DoVer addendum).

> Status: harness scaffolded; **no experimental results yet.** No numbers here until a real,
> reproduced kill test exists (CLAUDE.md §5 — README milestones only).

## How the kill test wires together (once traces + oracle labels exist)

1. **Generate** ~30 failing traces on the pinned Ollama model (`harness.runner.run_agent` +
   `harness.recorder`). Provenance = fresh traces (work-plan §8 item 1).
2. **Label** each trace with ARIA's decision tree, recording BOTH the `failure_class` and the
   oracle `failure_step_k` (§8 item 2).
3. **Verify** ground truth deterministically (`harness.verifiers`) → `answer_correct` (§8 item 4).
4. **Replay** each trace at its `failure_step_k` under each arm in
   `harness.interventions.KILL_TEST_INTERVENTIONS` (no_op, reflect_and_retry, rollback_2,
   requirement_injection), N times (`harness.replay.replay_cell`).
5. **Score** with `harness.metrics`: the recovery matrix, and the iatrogenic rate vs no_op.

**Kill-test verdict:** recovery rates differ sharply across failure classes (≥1 class an
intervention clearly helps, ≥1 class where reflect_and_retry is flat or net-harmful) → build the
study. All cells roughly equal → the matrix premise fails; pivot.

Run config: `paper-recovery/configs/kill_test.yaml`.
