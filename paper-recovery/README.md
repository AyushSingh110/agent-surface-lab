# paper-recovery (Ideas A + B)

**Spine (mechanism-level reframe, 2026-07-22):** a capable instruction-tuned agent rarely loops,
skips deliverables, or misuses *erroring* tools. It fails in two specific, reproducible ways —
**(1) skipped-lookup hallucination** (fabricating a fact that was available but unfetched) and
**(2) silent tool misuse** (misusing a *working* tool with no error evidence). This work
characterizes both, measures which interventions recover each, and identifies where standard
self-correction makes them worse. The **iatrogenic rate** vs a **no-op control**, measured by
counterfactual replay, remains the spine — re-aimed at failures that actually occur. Silent tool
misuse is a taxonomy gap the counterfactual-repair cluster (DoVer/CausalFlow/CAR) is structurally
blind to. See `docs/work-plan.md` §2/§2.0, `docs/task-family-v2.md`, and `docs/RESEARCH-NARRATIVE.md`.

> Status: harness + sandbox scaffolded; pilots run. **All pilot numbers are PROVISIONAL** pending
> the verifier audit (see `docs/RESEARCH-NARRATIVE.md`). No results in this README until a real,
> reproduced, audit-clean result exists (CLAUDE.md §5 — README milestones only).

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
