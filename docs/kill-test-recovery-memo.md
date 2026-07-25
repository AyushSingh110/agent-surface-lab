# Kill-Test Memo — Recovery sweep (first intervention measurement)

*Written regardless of outcome, per the kill-test discipline. **n = 8 traces. Every number here is
DIRECTIONAL, not a result.** This is the first time an intervention was ever applied to a trace in this
project; the question it answers is narrow: **does anything move?** Backbone qwen2.5:7b, temp 0.7,
N=3 replays/cell, seed 20260721. Labels are the human's; oracle k per `labels.json`.*

**Date:** 2026-07-22. Raw data: `data/repilot/recovery/results.json`.

---

## The sweep

8 human-labeled failing traces × 4 interventions × 3 replays = **96 replays**. The 8 traces span three
mechanisms: **hallucination-by-skipped-lookup** (DR-4 ×2), **silent tool misuse** (DR-6 ×3), and a
**completion slip** (CO-1 ×3, labeled goal_misalignment). `no_op` (re-run from k unchanged) is the
control.

## Recovery rate by (intervention × mechanism) — DIRECTIONAL

| intervention | hallucination (n=2, **N=10**) | silent tool misuse (n=3, N=3) | completion slip (n=3, N=3) |
|---|---|---|---|
| **no_op** (control) | 0.55 | **0.00** | 0.00 |
| reflect_and_retry | 0.90 | **0.00** | **0.67** |
| rollback_2 | 0.60 † | **0.00** | 0.00 |
| requirement_injection | **0.00–1.00 ‡** | **0.00** | 0.00 |

Hallucination cell raised to **N=10** (20 replays/arm); other cells remain N=3 (directional).
**† `rollback_2` here is `restart_clean`** (k=1 clamps to step 0 — see the degeneracy note below).
**‡ `requirement_injection` is phrasing-dependent** and swings from 0.00 to 1.00 — see §"Requirement-phrasing
confound" below. The single number is meaningless; that row must be read as the phrasing table.

> **⚠ `rollback_2` degeneracy (correction).** `rollback_2` rewinds `n=2` from the oracle step `k`, clamped
> at 0. On the traces with `k=1` — **hallucination (DR-4) and silent tool misuse (DR-6)** — it clamps to
> step 0 with resume-context == the initial system+user messages, i.e. it is **functionally
> `restart_clean`**, not a two-step rewind (verified: all five k=1 traces resume at turn 0 with the initial
> 2-message context). So **"rollback_2 recovers hallucination 1.00" actually reads "restarting a 2-step
> task from scratch succeeds 100%"** — a much weaker and less interesting claim. Only the **completion slip
> (CO-1, k=6)** exercised a genuine 2-step rewind (to step 4), where it recovered 0.00. The
> `restart_clean`-vs-`rollback` distinction is a real intervention we have not separated at these short
> trace lengths; v2 traces are longer and will let `rollback_n` be tested as intended.

## What moved — four directional findings

**1. Something moves. This is NOT a null.** The four arms behave differently from each other and from
`no_op`, and the pattern **depends on the mechanism**. That is the class/mechanism × intervention
structure the study was premised on, now visible at the mechanism level.

**2. Silent tool misuse is unrecoverable by every arm (0/9 each, including no_op).** Nothing — not
reflection, not rollback, not requirement injection — fixes the date-as-integer error. The reason is
structural and is the whole point of the §2.0 taxonomy gap: the tool returned a well-formed `194.0`,
so there is **no error signal for any generic repair to latch onto**, and the model keeps trusting the
tool's false validation. The failure class that the counterfactual-repair cluster (DoVer/CausalFlow/CAR)
is blind to is also the one generic repair cannot touch here. (n=3, one task shape — an observation.)

**3. ~~Iatrogenic harm from requirement_injection~~ — RETRACTED. The effect was a phrasing artifact.**
The first sweep showed `requirement_injection` recovering hallucination 0/6 vs no_op 4/6, and I framed
it as "requirement injection is iatrogenic." **A follow-up confound test (N=10, 4 phrasings of the same
requirement) shows that framing is wrong** — see the phrasing section below. The general claim does not
hold; what holds is a narrower, different, and arguably more interesting statement about *surface
wording*. The original framing is withdrawn in full, not defended.

**4. The interventions are differentiated, not interchangeable.**
- `reflect_and_retry` is robust: it helps the completion slip (0.67 — prompted to review, the model notices
  the missing operand and finishes the sum), helps hallucination (0.90 at N=10), and is **never worse than
  no_op** in any cell — the "safe" arm.
- A **neutrally-phrased requirement is the *best* arm** on hallucination (1.00, beating reflect's 0.90) — but
  only when phrased without the "only" cue (see the phrasing section).
- `rollback_2` "recovered" hallucination 1.00 in the first sweep — but that was **`restart_clean` in
  disguise** (k=1 clamps to step 0; see the degeneracy note), not a rewind, and at N=10 restart lands at
  0.60 ≈ no_op. On the completion slip (CO-1, k=6, a *genuine* 2-step rewind to step 4) it recovered 0.00:
  rewinding discards the partial sums, so the model redoes the work and stops early again.

## Requirement-phrasing confound — RESOLVED (the finding is about surface wording, not injection)

The original iatrogenic result used one requirement string containing the word **"only"**. That word is
itself pressure toward answering immediately, so the effect might be an artifact of the phrasing rather
than a property of requirement injection. Tested on DR-4 (n=2) at **N=10** with four phrasings of the
*same* requirement (identical wrapper, only the requirement clause varies), against the no_op baseline:

| requirement phrasing | recovery (20 replays) | vs no_op 0.55 |
|---|---|---|
| **(a)** "Report **only** #150's manager's name." | **0.00** | catastrophic — well below no_op |
| **(b)** "The answer must be #150's manager's name." | **1.00** | strongly HELPFUL — best arm |
| **(c)** "Report #150's manager's name; use tools to verify." | **1.00** | strongly HELPFUL |
| **(d)** "Report #150's manager's name." (no "only") | **0.30** | mildly harmful |

**Verdict: the effect does NOT reproduce across phrasings — the iatrogenic framing is retracted.** The
same intervention, same intent, swings from **0.00 to 1.00** on wording alone.

**Attribution (HYPOTHESIS from ONE task — DR-4; not an established effect).** It is *not* the word "only":
(d) has no "only" and still lands at 0.30, below no_op's 0.55. The split that fits the data is
**imperative action vs declarative constraint**:
- **(a), (d) are imperatives** — they *command* the agent to "Report … the name," i.e. to act/answer now.
  Both underperform no_op (0.00, 0.30).
- **(b), (c) are declarative / permissive** — (b) *describes a property the answer must satisfy* ("the
  answer must be …"), (c) *permits the corrective step* ("… use tools to verify"). Both hit 1.00.
- **"only" is an intensifier, not the cause:** it deepens the imperative from 0.30 (d) to 0.00 (a).

The plausible mechanism: an imperative to "report the name" pushes the model to emit a name immediately and
skip the second lookup, while a declarative/permissive framing leaves room to keep working. **(c) is
imperative-but-lookup-permitting**, so the operative factor may be more precisely *"does the phrasing
license the corrective action vs demand an immediate answer."* This needs testing across many task shapes
before it is anything more than a one-task hypothesis (v2, directive 3).

**Why this matters:** it is dead-on the program thesis — *the agent acts on the surface FORM of the repair
instruction, not its meaning.* An identical requirement helps or destroys recovery depending on
imperative-vs-declarative wording. So **repair phrasing is a primary variable**, not a single "requirement
injection" arm.

## Iatrogenic table (per-trace, strictly worse than no_op)

| mechanism | reflect_and_retry | rollback_2 (=restart) | requirement_injection |
|---|---|---|---|
| hallucination (n=2, N=10) | 0/2 worse | ~tie (0.60 vs 0.55) | **phrasing-dependent (a: worse; b/c: better; d: worse)** |
| silent tool misuse (n=3) | 0/3 | 0/3 | 0/3 |
| completion slip (n=3) | 0/3 (3/3 better) | 0/3 | 0/3 |

## Honest caveats — hold these firmly

- **n = 8. Directional only.** No significance is claimed; these are hints, not effects.
- **`no_op` already recovers hallucination 0.67** — the model frequently self-corrects a skipped lookup
  on a fresh run. So hallucination is "easy," and the *interesting* contrast is #3: an intervention that
  *breaks* that self-correction.
- **Silent tool misuse rests on one task shape (DR-6, n=3).** Its 0.00-everywhere result is clean but
  narrow; establishing it needs the v2 silent-misuse family with controls.
- **Near-boundary cells** (rates near 0.5 at N=3 — e.g. no_op hallucination 0.67, reflect completion
  slip 0.67) would need higher N to firm up.
- Recovery here is scored by the **hardened, audit-clean** verifiers; the two documented residual verifier
  limitations (TM-5, CO-5) do not involve any task in this sweep.

## Verdict

**The recovery premise is alive, not dead — but two of the four original headline claims were corrected
by follow-up checks, which is exactly what the checks are for.** After correction, what stands is:
- interventions **move** and **differ by mechanism** (not a null);
- **silent tool misuse is unrecoverable by every arm** (0/9) — no error signal to repair against;
- **requirement injection is phrasing-sensitive**: a neutral/permissive requirement is the *best* arm on
  skipped-lookup hallucination (1.00), while the surface cue "only" is catastrophic (0.00) — an
  instruction the agent obeys on its surface wording, not its intent;
- **reflect_and_retry** is robust and never worse than no_op (0.90 hallucination, 0.67 completion slip).

Two retractions/corrections vs the first sweep: the "requirement_injection is iatrogenic" claim is
**withdrawn** (phrasing artifact), and "rollback_2 recovers hallucination 1.00" is **corrected** to
"`restart_clean` on a 2-step task" (rollback_2 degenerated at k=1). None of this kills the study; it
sharpens it and hands the paper a cleaner, thesis-aligned result (surface wording of the repair matters).
It does **not** prove anything at this n; it justifies building the v2 families — and adds a new required
factor: **requirement phrasing** must be a controlled variable, not a single arm.

**Next (not started, awaiting human):** scale via the v2 task families (skipped-lookup + silent misuse),
raise N on near-boundary cells, and — once v2 shows a real hit rate — the second-backbone generalization
check.
