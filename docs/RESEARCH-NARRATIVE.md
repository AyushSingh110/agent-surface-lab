# Research Narrative — `agent-surface-lab` / paper-recovery

*A synthesized, rewritten account of this project — written to be read end-to-end by a technical
person who has never seen it, so they can understand and defend it cold (interview, viva, supervisor
meeting). This is **not** the logbook. `LOGBOOK.md` is the append-only, chronological reproducibility
record; this document is a living synthesis that gets **rewritten** as understanding improves.
Superseded reasoning is kept but marked. Numbers that have not survived the verifier audit are labeled
**PROVISIONAL**. Nothing here is written to impress; it is written to be true under questioning.*

**Last synthesized:** 2026-07-22, after the confirmatory re-pilot and the verifier adversarial audit.

---

## 1. The question, and why it matters

When an LLM agent fails partway through a task, a production on-call engineer's real question is not
"which step broke?" but the *next* one: **now that it's failing, what do I do, and will doing something
make it better or worse?** Teams bolt on "reflect and retry" or "self-correction" loops on the
assumption that intervening helps. That assumption is largely untested at the level of *which
intervention works on which kind of failure* — and it is entirely plausible that generic reflection is
net-harmful on some failures (it rationalizes a wrong answer more fluently) where a blunt rollback
would have worked.

The distinctive methodological commitment is that we measure recovery **causally, by counterfactual
replay**: take a failing recorded run, rewind to the failure step *k*, apply an intervention, re-run
forward, and check the *actual* outcome against deterministic ground truth. This is a real
counterfactual, not an LLM judge's opinion about whether a fix "looks better."

The program-level thesis this study sits under: **LLM agents act on surface text and surface cues
rather than the deeper property those cues are supposed to represent** — descriptions instead of
capability, words instead of consequence, a detected failure instead of a recoverable one.

---

## 2. Where this sits in the literature (and how our framing was forced to sharpen)

The agent-failure field is saturated on **detection and attribution**: Who&When and Who&When Pro,
AgenTracer, GraphTracer, ErrorProbe — all answer "which agent/step caused the failure." Almost none ask
whether detection is *actionable*.

The uncomfortable finding of our literature scan was that the **repair** neighbourhood filled in fast
during 2025–2026, and it partially scoops the framing we started with:

- **DoVer** (arXiv:2512.06749) reframes debugging from attribution toward *recovery*: it intervenes at a
  step and validates by in-place replay (milestone/utility progress), recovering ~49% of failed trials
  in its best setting. It is multi-agent and uses a milestone metric, not deterministic ground truth.
- **CausalFlow** (2605.25338) does causal attribution **plus minimal counterfactual repair**.
- **Causal Agent Replay** (2606.08275) formalizes do-operations replayed under the same stochastic
  policy.

**Consequence for us:** the bare claim "detection is not repair — intervene and verify by replay" is no
longer novel; DoVer/CausalFlow/CAR occupy it. What none of them do is measure the **iatrogenic rate**
(interventions that make outcomes *worse* than doing nothing) — none has a **no-op control** on runs
that might self-recover. That, plus a **class/mechanism-conditional** accounting and the bridge to
**cost-aware early prediction** (Idea B), is where our contribution survives. See §4 for how a later
empirical result forced a second, sharper reframe to the *mechanism* level.

(The sibling study `paper-toolseo` was similarly checked: its original headline — description text buys
tool-selection share at fixed capability — is largely scooped by *Agent-Facing Information Design*
(2605.23916) and *BiasBusters* (2510.00307); its live gap is persistence-after-failure + an
outcome-based defense. That study is deferred and not the subject of this narrative.)

---

## 3. Significant decisions — what, alternatives, why, and cost

Each decision is stated with the alternative we rejected and what choosing this one cost us.

**3.1 One shared harness, monorepo, sequential studies.** *Alternatives:* one big platform; five
separate repos. *Why:* reviewers reward one clean question; the engineering under the studies is nearly
identical, so a reusable harness compounds. *Cost:* discipline required to keep `harness/`
study-agnostic (experiment specifics live in `recovery_sandbox/`, not the harness).

**3.2 Ollama-only backbone (dropped Groq).** *Alternative:* a Groq-hosted + Ollama pair. *Why:* the
human chose a single local backbone; no hosted-API dependency or secrets. *Cost:* slower inference on
consumer hardware; no large-model comparison unless explicitly added.

**3.3 Trace provenance = generate fresh (Option C), not reuse ARIA.** *Alternatives:* reuse ARIA's
existing traces as-is; reuse + relabel. *Why:* ARIA's traces were generated on Groq
`llama-3.1-8b-instant`; replaying them forward on Ollama would mix backbones and dirty the
counterfactual. Fresh generation keeps record and replay on one model. *Cost:* we must build a runner +
recorder before we can produce any traces, and we re-label from scratch.

**3.4 Labeling = adopt ARIA's decision-tree guide verbatim.** *Alternative:* invent a new taxonomy.
*Why:* ARIA already ships an operational, decision-tree labeling guide with the exact five classes;
reusing it gives continuity and a tested protocol. *Cost:* inherits ARIA's class boundaries, which the
mechanism-level reframe (§4) later shows are the wrong cut for a capable model. Single labeler at
kill-test scale; two-annotator + Cohen's κ reserved for the full study.

**3.5 Deterministic ground truth, never an LLM judge.** *Alternative:* an LLM-as-judge scorer.
*Why:* a counterfactual outcome must be checkable and reproducible; an LLM judge reintroduces the
surface-text problem we study. *Cost:* writing per-task-type verifiers (exact-match / fact-match /
file-written), and — as §4 shows — **rigid string verifiers turned out to be the single biggest risk in
the project** (they silently misclassify correct answers).

**3.6 Replay determinism = sample N≥3 and report a distribution (Option b).** *Alternative:* a single
deterministic replay (seed + temperature 0). *Why:* a single sample can masquerade as a recovery or a
failure under a stochastic policy; a distribution is honest about variance and lets us raise N near a
decision boundary. *Cost:* ~N× the compute per cell. Seed, temperature, and model tag are logged on
every replay.

**3.7 Backbone pin = qwen2.5:7b.** *Alternative:* llama3.1:8b (ARIA's family — continuity). *Why:* a
head-to-head tool-calling smoke test showed llama3.1:8b fails multi-step tool-argument threading ~100%
of the time (it passes the literal token "result" as an argument), while qwen2.5:7b threads cleanly 6/6.
A model that can't chain tools would flood the traces with one artifact. *Cost:* drops the ARIA
model-family continuity (acceptable — we generate fresh traces anyway).

**3.8 Detection step *k* = oracle-labeled.** *Alternative:* a real detector chooses *k*. *Why:* the
kill test isolates *repair* from *detection*; an oracle *k* is a cleaner counterfactual than DoVer's LLM
localizer. *Cost:* the kill test does not yet speak to detector quality (that is Idea B's job).

**3.9 max_turns = 8 (re-pilot).** *Alternative:* 12. *Why:* a realistic production tool-call budget; a
`max_turns` stop is a legitimate "task exceeded budget" event, tagged `stopped_reason="max_turns"` and
counted **separately** from an in-run failure. *Cost:* genuinely long tasks (e.g. ten sequential adds)
fail by budget — which is why we separate that bucket rather than miscount it as context_overflow.

**3.10 Do NOT switch backbones to populate empty classes.** *Alternative:* generate stubborn classes on
a messier model. *Why:* that would confound the model variable to rescue a five-class matrix that the
data says does not exist. *Cost:* we accept empty cells and a reframe (§4) rather than a fuller-looking
but dishonest matrix. (A second backbone is reconsidered later as a *generalization check*, not a
confound.)

---

## 4. Significant results — what we ran, what came back, what it meant, what changed

This is the heart of the project so far. Two of these are corrections of our own mistakes; they are the
methodological spine of the paper, not embarrassments to hide.

**4.1 Pilot 1 (20 runs, max_turns 12).** Only 4/20 runs failed. The classes we predicted were *easiest*
to induce — goal_misalignment and tool_misuse — produced **zero** failures; the model wrote every
deliverable and handled every erroring tool. *Meaning:* a capable instruction-tuned 7B is simply
competent on most of these induction tasks. *Change:* triggered the human's decision not to force a
five-class matrix.

**4.2 First verifier false-negative (HL) — a correction.** On inspection, two of the four "failures"
(HL-3, HL-4) were **not** failures: the model answered honestly ("did not yield any results", "could not
be found"), but the verifier used a fixed honesty-phrase list that did not contain those phrasings, so
honest answers were scored as failures. *Meaning:* the reported `hallucination = 0.50` was a
**measurement artifact**; the model did not hallucinate on absent-fact tasks at all. *Change:* replaced
the phrase list with a robust rule — **correct iff the output asserts no fabricated number/date and no
spelled-out magnitude the prompt did not supply** (`no_fabricated_value`). This credits any honest
wording and fails only on a fabricated figure.

**4.3 Human labels on the two real pilot-1 failures.** DR-4 → *hallucination_loop* (the tool returned
`manager=#77`; the model skipped `get_record(77)` and invented a name). CO-1 → *completion slip*, closest
to goal_misalignment (six clean adds, no loop, stopped one operand short). *Meaning:* the model's real
failures did not land in their intended classes, and hallucination appeared where *drift* was intended —
class labels were the wrong lens.

**4.4 Re-pilot (84 runs, max_turns 8).** As first scored: 11 induced failures + 6 budget-exceeded of
84. **After the verifier audit and re-scoring (§4.7): 8 induced failures + 6 budget-exceeded.**
**hallucination_loop = 0/18** — the model never fabricated on absent-fact tasks; it is *honest when
tools return nothing*.

**4.5 Two more verifier false-negatives — the pattern crystallizes.** Reading every induced failure
showed 3 of the 11 were **not** model failures: **TM-3 ×2** (the model correctly said "could not be
found" / "does not exist", but the GT `fact_match("not found")` didn't match those phrasings) and
**GM-2 ×1** (the model wrote a valid 3-row comparison but labeled rows "1./2./3." instead of "#1/#2/#3",
so a formatting-rigid check failed). *Meaning:* **real induced failures ≈ 8, not 11**, and — more
importantly — three rigid-string false-negatives in a row is a *systematic* risk: every recovery rate we
will ever compute has "did this run fail" as its denominator, and a false-positive failure rate corrupts
the entire matrix while throwing no error. *Change:* a full **adversarial verifier audit** was made the
top priority (§4.7).

**4.6 The genuine failure surface (observable behavior; realized labels are the human's).**
*Post-hardening, the re-pilot's 8 induced failures are exactly three behaviours: DR-4 ×2, DR-6 ×3,
CO-1 ×3 — with tool_misuse, goal_misalignment and hallucination_loop all at **zero**.*
- **Hallucination-by-skipped-lookup (DR-4):** the model fabricates a fact that was *available but
  unfetched* (it had `manager=#77` and invented a name rather than making the second call). ~2/3.
- **Silent tool misuse (DR-6):** the model fed dates to `subtract` as raw integers
  (`20260915 − 20260721 = 194`) instead of computing 56 calendar days — a **working** tool, **no error**,
  a wrong answer traceable to a real tool result. ~3/3.
- Minor: completion slips / empty outputs (CO-1); budget-exceeded on genuinely long tasks (CO-6, GM-3).
- **Essentially zero** clean context_overflow (looping), tool_misuse (misusing an *erroring* tool), or
  deliverable-skip. The surface is **narrow and mechanism-shaped**, not class-shaped.

**4.7 Verifier adversarial audit, hardening, and re-scoring (Directive 1).** A committed battery
(now **199 cases**: ≥3 correct phrasings + ≥4 wrong near-misses per task, weighted toward wrong cases
because false positives are the silent direction) surfaced **7 mismatches across 4 patterns**:
(a) **TM-3** rigid absence phrasing (false-negatives); (b) **GM-2** rigid `#N` deliverable formatting
(false-negatives); (c) **CO-4** spelled-out "two" unrecognized (false-negative); (d) **DR-5** a
**false-positive** — "212 K" (right number, wrong unit) scored correct because the numeric check ignored
units. The false positive is the dangerous kind: it *under*-counts failures and therefore silently
*inflates* recovery rates.

Four hardened rules were approved and applied: robust **`acknowledges_absence`** (negation-of-existence
**AND** the fabrication guard), **name-based** deliverable checks for GM-2, **digits-win-else-spelled**
numeric matching, and **`numeric_with_unit`** (applied to DR-5, TM-6, DR-6 after auditing every numeric
task for unit-ambiguity).

**A fix introduced its own bug — and re-scoring caught it.** The first `acknowledges_absence` banned any
mention of a content term, which wrongly failed the real model output *"...does not exist, so I cannot
read its first line."* The rule now tests for an **assertion** of content (term + copula + value), so a
negated mention passes while the hedge *"...does not exist, but the first line is probably 'Hello'"*
still fails. Both real outputs are now permanent battery cases.

**Two residual limitations are documented, not patched** (patching them would trade rare false positives
for common false negatives): any-number-token matching can be fooled when the correct value appears as an
*intermediate* while a different final answer is asserted (TM-5); and extra spurious values in a
multi-value answer are not penalized (CO-5).

**Re-scoring both pilots with the hardened verifiers** flipped 5 runs, all false-negatives → correct:
pilot 1 **4 → 2** induced failures of 20 (HL-3, HL-4); re-pilot **11 → 8** induced failures of 84
(TM-3 ×2, GM-2 ×1). No run flipped the other way — the unit hardening added no new failures, meaning the
model did report units correctly. These re-scored figures are **no longer provisional**.

**4.8 First recovery measurement — the 96-replay kill test, and two self-corrections (DIRECTIONAL, n=8).**
The whole project to this point had built and hardened the *trace generator*; no intervention had ever
been applied. The first sweep (8 labeled failing traces × 4 interventions × 3 replays) answered "does
anything move?" — and it did (full memo: `docs/kill-test-recovery-memo.md`). But two follow-up checks
then corrected two of the four headline claims — which is exactly what the checks exist for, and the
corrections are themselves the most honest part of the story.

What stands after correction: (i) interventions **move and differ by mechanism** — not a null;
(ii) **silent tool misuse is unrecoverable by every arm** (0/9, incl. no_op) — no error signal for repair
to latch onto, corroborating the §2.0 gap; (iii) **`reflect_and_retry` is robust** (0.90 hallucination,
0.67 completion slip, never worse than no_op).

**Correction A — the iatrogenic claim is RETRACTED, and its replacement is a hypothesis about wording.**
The first sweep showed `requirement_injection` recovering hallucination 0/6 vs no_op 4/6, framed as
"requirement injection is iatrogenic." A confound test (N=10, four phrasings of the *same* requirement)
demolished that framing: recovery swings from **0.00 to 1.00 on wording alone** — (a) imperative
"report **only** …name" → 0.00, (b) declarative "the answer must be …name" → 1.00, (c) "report …name;
use tools to verify" → 1.00, (d) imperative "report …name" → 0.30. The tempting "it's the word only" read
is *also* wrong: (d) has no "only" and still underperforms no_op (0.55). The pattern that fits is
**imperative action (a, d) vs declarative/permissive constraint (b, c)** — a command to "report the name"
makes the model answer immediately and skip the corrective lookup, while a declarative or lookup-permitting
framing leaves room to keep working; "only" is an *intensifier* (0.30 → 0.00), not the cause. This is a
**one-task hypothesis (DR-4)**, to be tested across task shapes in v2. It is more thesis-aligned than the
retracted claim — *the agent acts on the surface FORM of the repair, not its meaning* — and it promotes
**repair phrasing to a primary research variable**, not a single arm.

**Correction B — "rollback_2 recovers hallucination 1.00" is corrected to `restart_clean`.** rollback_2
at k=1 (DR-4, DR-6) clamps to step 0, so it was functionally a clean restart of a 2-step task, not a
2-step rewind; at N=10 it lands ~0.60 ≈ no_op. Genuine rollback was only exercised on the completion slip
(k=6), where it recovered 0.00.

**n=8, so nothing is a *result*.** But the premise is alive, sharpened, and — after two honest
retractions — cleaner than before. Worth scaling to v2, with requirement-phrasing as a controlled factor.

**4.9 The reframe these results forced (mechanism level).** We do not force a five-class matrix. New
spine: *a capable instruction-tuned agent rarely loops, skips deliverables, or misuses erroring tools; it
fails by (1) skipped-lookup hallucination and (2) silent tool misuse.* The key generalization: **failure
rate is a property of task STRUCTURE, not failure class** — class averaging hid two near-deterministic
inducers (DR-4, DR-6) among four inert drift tasks. **Silent tool misuse is a taxonomy gap** (see
`work-plan.md` §2.0): by ARIA's rules it is neither tool_misuse (no error evidence) nor
hallucination_loop (the number came from a real tool result), and the whole counterfactual-repair cluster
(DoVer/CausalFlow/CAR) is **structurally blind** to it because their detectors depend on error/anomaly
signals that do not exist here. The iatrogenic-rate contribution and the no-op control remain the spine,
re-aimed at these two mechanisms.

**4.10 The v2 recovery sweep — the recovery signal, confirmed at real n, with the DR-4 hypothesis
corrected (DIRECTIONAL; single model, N=3; skipped-lookup n=50, surface-form n=31).** After scaling the
two mechanisms into v2 task families (skipped-lookup at chain depths 1–3; surface-form misuse over
dates/HHMM/version), labeling the failing runs, and sweeping 8 arms × the pools, two headline results
emerged (full memo: `docs/recovery-v2-results.md`), both spot-checked in replay against real behavior:

- **Skipped-lookup is recoverable — but by ACTION-LICENSING repairs, not by grammatical mood.** The
  earlier DR-4 "declarative beats imperative" hypothesis is **refuted**: `declarative_neutral` ("the answer
  must be X") is among the *worst* arms (~0.24), below `imperative_plain` (~0.55). What recovers is a
  repair that explicitly *licenses the corrective action* — `declarative_lookup_permitting`
  ("...use tools to verify", up to 1.00) and `reflect_and_retry` ("review your work", ~0.8 across depths).
  Verified: those arms make the previously-skipped lookup; `declarative_neutral` does not. Recovery
  **degrades with chain depth** (RQ3 lateness is real); `no_op` ≈ 0 (deep skips don't self-recover); no
  arm is iatrogenic here. This *refines* the surface-cue thesis: the operative dimension of the repair's
  surface form is whether it licenses the fix, not its mood.
- **Surface-form misuse is recovery-RESISTANT.** Date and HHMM misuse resist every arm (≤ 0.15) — no
  text-level repair removes the tool's *false validation* of a wrong number. This confirms the §2.0 gap at
  real n and sharpens it: the corrupting signal is a tool result, not a prompt, so prompt-level repair
  cannot reach it. (The dotted-version sub-family, n=6, is a noisy outlier and carries no weight.)

Two DR-era claims have now been corrected by follow-up work — the "iatrogenic requirement injection" claim
(→ phrasing-sensitivity) and the "imperative vs declarative" claim (→ action-licensing). Both corrections
strengthen the account; they are recorded, not hidden.

**Firm-up (Step 1, N=10 on the argument-critical cells): the contrast HOLDS, it did not soften.** At N=10,
`declarative_neutral` stays low at every depth (0.16 / 0.18 / 0.20) — worst at depths 1–2, below
`imperative_plain` (0.66 / 0.42) — while the action-licensing arms stay high (`lookup_permitting`
1.00 / 0.75 / 0.60; `reflect` 0.60 / 0.83 / 0.60). Two declaratives (`neutral` vs `lookup_permitting`)
differ only by the licensing clause, and by ~0.6–0.8 in recovery — so the driver is licensing, not mood.
Surface-form (date+hhmm) at N=10 stays ≤ 0.14 across all arms: recovery-resistant, firmly. Both headlines
survive the harder n.

**4.11 Second backbone (Mistral 7B): the generalization check, and what it can and cannot say.** Per the
sequencing rule, after the recovery signal was confirmed on qwen, a narrow generalization check ran on a
different-family model (mistral:7b), which needs its own failing traces (no cross-model replay). Three
outcomes, all honest: (1) **skipped-lookup hallucination GENERALIZES** — Mistral fabricates the unfetched
value too (reads `manager=#202`, invents "John Smith" without calling `get_record(202)`), so the mechanism
is confirmed cross-model, no longer qwen-only. (2) **Surface-form ("tool false-validation") misuse is
MODEL-CONDITIONAL** — it reproduced in only 3/81 Mistral traces because Mistral does not reflexively apply
the arithmetic tool to numeric-looking strings (it reasons in text). Framed as a finding with a named
precondition: *this misuse occurs in tool-reflexive models, and where it occurs it is unrecoverable by
text repair* — which tells a practitioner **which** agents are vulnerable. (3) **Recovery generalization is
UNTESTABLE at local-7B** — 34/81 Mistral failures are tool-emission pathologies, and every recovery arm
depends on the model re-issuing a tool call, so "failed to recover" cannot be separated from "couldn't
emit a tool call." Rather than force a muddy number, the recovery sweep was **not run** on Mistral; the
tool-capability confound is itself reported as a methodological caution. (Full: `docs/recovery-v2-results.md`.)

---

## 5. Current status, open questions, known limitations

**Status.** Harness built and tested (recorder, replay+reconstruct, interventions incl. a first-class
no-op control, metrics, deterministic verifiers). Sandbox + 28-task v1 suite built. Two pilots run.
Verifier audit committed and applied; pilots re-scored. Framing reframed to the mechanism level. **The
first recovery kill test has now run (96 replays, n=8, directional):** interventions move, differ by
mechanism, and show a verified iatrogenic case and a clean unrecoverable case — enough to justify scaling,
not to claim an effect. README still carries no results (correctly — n=8 is a kill test).

**Numbers are now audit-backed, with two documented exceptions.** The four hardened rules are applied
and both pilots re-scored (§4.7), so the headline counts — pilot 1: **2 induced failures / 20**;
re-pilot: **8 induced + 6 budget-exceeded / 84** — are no longer provisional. The two residual verifier
limitations (TM-5 intermediate-value, CO-5 spurious-extra) remain open and are recorded in the audit
guard; neither affects any observed pilot run.

**Status is now past exploration.** The v2 families were built, labeled, and swept; the recovery findings
are established on qwen at real n (skipped-lookup n=50, surface-form n=31), the argument-critical cells
firmed at N=10, and the second-backbone check run. **The next phase is WRITE-UP, not more runs**
(`docs/paper-outline.md`).

**Open questions.**
1. Whether the recovery findings (action-licensing; text-repair resistance) are **model-general** —
   currently demonstrated on one model; the second-backbone check confirmed only the *mechanism*, not
   recovery, because of the tool-capability confound. A cleaner cross-model recovery test needs a
   tool-reliable model, which is scarce at local-7B under the Ollama-only constraint.
2. Firming the remaining **near-boundary, N=3 mid-range cells** if a reviewer wants tighter estimates.
3. The sibling **`paper-toolseo`** study (deferred): the second surface where the same thesis is expected.

**Known limitations (stated plainly; see `recovery-v2-results.md` "Limitations and scope").**
- **Single primary model (qwen2.5:7b)** for all recovery results; generalization of *recovery* untested.
- **Synthetic sandbox** (deterministic record chains / date-clock strings) — buys clean counterfactuals
  and audited ground truth at the cost of unestablished external validity to real workloads.
- **Directional n on some cells** — headline extremes firm at N=10, but several mid-range rates sit near a
  decision boundary and are read as directional.
- **Tool-capability confounds cross-model recovery evaluation** — a model must be tool-reliable enough to
  exhibit the mechanism *and* respond to a tool-based repair; only qwen met that bar at 7B. Reported both
  as a limitation and as a methodological result.
- **Single-labeler labels** (assisted, spot-check-validated); no κ at this scale.
- **The verifier is a first-class threat to validity**, not plumbing — the adversarial audit is a standing
  guard; every task enters the battery before it is run.

---

*Maintenance rule: update this document at every significant decision or result, alongside the LOGBOOK
entry. Rewrite sections as understanding improves; keep superseded reasoning visible and marked with the
reason it was superseded.*
