# Work Plan — `agent-surface-lab`

*Planning document. No code. Derived from `individual-research-plan.md` and governed by `CLAUDE.md`.
This plan states how the engineering will be sequenced; it does **not** change any experimental
design, baseline, or metric — those are the human's to own. Where I think a design choice is yours
to make, it is listed in the final section rather than decided here.*

Unifying thesis across all studies: **LLM agents act on surface text and surface cues rather than
the deeper property those cues are supposed to represent.**

Backbone configuration (per updated `CLAUDE.md`): **a single local Ollama model + one agent
scaffold.** No hosted APIs.

---

## 1. The three studies at a glance

| Study | Dir | Idea(s) | One-line finding it chases |
|---|---|---|---|
| Recovery | `paper-recovery/` | A + B | *Detection is not repair* — predict failure early, intervene, verify causally. |
| ToolSEO | `paper-toolseo/` | C | *Descriptions are an adversarial surface* — selection share can be bought with text alone. |

Idea A and Idea B ship as **one paper** (prediction → action → causal verification). Idea C is the
second paper. Ideas D and E from the research plan are **out of scope** for this plan and are not
built unless you explicitly ask.

---

## 2. Study 1 — `paper-recovery` (Ideas A + B): *How capable agents actually fail, and what repairs it*

> **MECHANISM-LEVEL REFRAME (2026-07-22, DECIDED by human — supersedes the two framings below).** The pilots
> showed a capable instruction-tuned 7B (qwen2.5:7b) **does not** loop, skip deliverables, or misuse *erroring*
> tools in any reliable way — three of the five ARIA classes were empty, not thin. Forcing a five-class matrix on
> this model is not defensible. Instead we go to the **mechanism level**. New spine:
>
> *A capable instruction-tuned agent rarely loops, skips deliverables, or misuses erroring tools. It fails in two
> specific, reproducible ways: (1) it **fabricates facts that were AVAILABLE but UNFETCHED**, and (2) it **misuses
> WORKING tools in ways that produce NO error evidence**. This work characterizes both, measures which
> interventions recover each, and identifies where standard self-correction makes them worse.*
>
> The driving observation: **failure rate is a property of TASK STRUCTURE, not failure class.** Class-level
> averaging hid two near-deterministic inducers — DR-4 failed 2/3 and DR-6 failed 3/3 while the other four drift
> tasks produced zero. The two mechanisms:
>
> - **Mechanism 1 — Skipped lookup (~67% observed).** A tool returns a *reference* to another record
>   (`manager=#77`); the model answers from invention rather than making the second call. (DR-4: fabricated a
>   manager name instead of calling `get_record(77)`.)
> - **Mechanism 2 — Silent tool misuse (~100% observed).** A *working* tool accepts semantically invalid input
>   without erroring (dates fed to `subtract` as raw integers: `20260915 − 20260721 = 194` instead of 56 calendar
>   days). (DR-6, all 3 runs.)
>
> **Mechanism 2 is a taxonomy gap and a contribution in its own right** (see §2.0). All observed numbers are
> **PROVISIONAL** pending the verifier audit (Directive 1). The **iatrogenic-rate contribution and the no-op
> control remain the spine** — we re-aim them at failures that actually occur, not abandon them. Cite
> DoVer/CausalFlow/CAR as the counterfactual-repair foundation; note (§2.0) they are structurally blind to
> Mechanism 2.

> **SUPERSEDED (2026-07-21) — "not all repair helps."** Prior spine: *"which intervention recovers which failure
> class, and where standard self-correction actively harms,"* with the iatrogenic rate central. **Why superseded:**
> still correct in spirit, but it presupposed a populated five-class matrix the pilots disproved; re-aimed at the
> two mechanisms above. The iatrogenic/no-op core carries forward unchanged.

> **SUPERSEDED (pre-2026-07-21) — "detection is not repair."** Retired because DoVer/CausalFlow/CAR already
> establish intervene-and-verify-by-replay. See `literature-review.md` Addendum.

### 2.0 The taxonomy gap: *silent tool misuse* (RATIFIED 2026-07-22)

**Operational definition.** A **silent tool misuse** is a step where the agent calls a *working* tool with
**semantically invalid arguments the tool accepts without error**, and then treats the (well-formed but
meaningless) result as valid. Diagnostic criteria, all required:
1. the tool returns a normal (non-error) result — no error string, no rejected/malformed call;
2. the arguments are valid *in type/shape* but wrong *in meaning* for the task (e.g. `YYYYMMDD` integers passed to a
   numeric `subtract` as if they were day counts);
3. the wrong final answer is *traceable to that tool result*, not invented from nothing;
4. **the tool result provides FALSE VALIDATION** — the agent receives a well-formed, non-error result from a
   working tool and treats it as *authoritative confirmation* of a semantically meaningless computation.

**Why it is a gap.** By ARIA's decision tree it is **not `tool_misuse`** (that requires error evidence — criterion
1 rules it out) and **not `hallucination_loop`** (the number came from a *real* tool result, not from thin air). It
falls between the classes. **Criterion 4 is what makes it tool-MEDIATED rather than an ordinary reasoning slip:**
the agent is not merely wrong in its head — it is wrong *because a working tool handed back something that looked
like evidence*, and the tool's silent acceptance functions as confirmation. Without criterion 4 a reviewer can
collapse the whole category into "the model reasoned badly." **The entire counterfactual-repair cluster is
structurally blind to it:** DoVer, CausalFlow, and CAR localize failures using error/anomaly signals that, by
criterion 1, *do not exist here* — there is nothing for their detectors to fire on. That blindness is itself a
finding.

**Evidential status — stated honestly.** This mechanism currently rests on **one task shape (DR-6) with n=3**. It is
an **OBSERVATION, not a validated class**. Establishing it as a class requires the v2 silent-misuse family (varying
the tool and the kind of silent invalidity), including the controls that test whether it survives when the correct
tool is available and when the unit is named. Until then it must be reported as a candidate mechanism with its n
stated.

### 2.1 Idea A — Recovery, not detection

**Central claim (sharpened).** Once a failure is detected at step *k*, whether an intervention *recovers* the run
depends on the (intervention × failure-class) cell — and, crucially, some standard interventions (reflect-and-retry)
are **net-harmful (iatrogenic)** on some classes relative to doing nothing. Recovery and iatrogenic harm are both
measured **causally by counterfactual replay against a no-op control**, never by an LLM judge.

**Research questions.**
- RQ1 — Per-intervention recovery rate, broken down by failure class.
- RQ2 — Iatrogenic rate: fraction of cases where intervening is *worse* than doing nothing.
- RQ3 — How recovery decays with detection lateness (catching at step 8 vs step 3).
- RQ4 — Is there a cheap policy (failure class, step) → best intervention that beats always-reflect and always-rollback?

**Hypotheses (the human's priors, restated — not mine to change).**
- H1 — Late `goal_misalignment` is unrecoverable without rollback.
- H2 — `tool_misuse` recovers cheaply via tool re-call (easiest cell).
- H3 — Reflect-and-retry has a **positive iatrogenic rate on hallucination** (the intended headline).
- H4 — Recovery decays sharply with detection lateness (this is what motivates Idea B).

**Intervention taxonomy (one axis).** No-op (control), re-anchor, rollback-*n* (n=1,2,3), tool re-call,
requirement injection, reflect-and-retry (the incumbent under test), restart-clean, escalate.

**Failure taxonomy (other axis).** drift, tool-misuse, context-overflow, hallucination, goal-misalignment.

**Baselines.** always-no-op, always-reflect, always-rollback, random-intervention policy. The learned/rule
policy must beat all four.

**Metrics.** recovery rate (per cell + overall), iatrogenic rate, net improvement over no-op, token/step cost
per intervention, cost-adjusted recovery-per-dollar.

**Headline figure.** The recovery matrix (intervention × failure class).

### 2.2 Idea B — Predictive failure as a cost-aware decision problem

**Central claim.** Eventual failure is predictable from a *partial* trajectory early enough to act, and the
right way to present this is **not** a classifier F1 but a **cost-aware early-stopping Pareto frontier**
(compute saved vs good runs killed).

**Research questions.**
- RQ1 — How early / how reliably can eventual failure be predicted from partial-trajectory features?
- RQ2 — Pareto trade-off: compute saved vs correct-runs-killed as the abort threshold sweeps.
- RQ3 — Under which cost structures does early abort dominate run-to-completion?
- RQ4 — Which trajectory features carry the signal, and do they transfer across task type / backbone?

**Hypotheses.**
- H1 — Loop-type failures (context-overflow, tool-error loops) are predictable *early* (signal is repetition);
  outcome-type failures (goal-misalignment) only *late*. The asymmetry is itself a finding.
- H2 — Agents are **not elastic** to the prediction — knowing failure is likely doesn't help without a working
  intervention (this is exactly why B needs A).
- H3 — A simple feature set (drift + repetition + error density) captures most of the signal.

**Method (as specified by the human).** Truncate per-step traces at step *k*; featurize (embedding-drift from
goal, tool-error density, step-repetition, self-contradiction, confidence markers, output-length dynamics);
train a lightweight predictor (logistic regression / XGBoost) for P(eventual failure | trajectory ≤ *k*); wrap
in a decision rule with an explicit cost model; sweep the threshold to trace the Pareto curve.

**Baselines.** predict-never (run all to completion), predict-always-fail (abort all — bounds the axis),
length-only heuristic, LLM-judge-at-step-*k*.

**Metrics.** Pareto curve (headline), AUROC/AUPRC per failure type per step, earliness (steps saved before the
true failure manifests), net cost saved under several cost models.

**Headline figure.** The tokens-saved vs correct-runs-killed Pareto frontier.

### 2.3 Why A + B are one paper

*Predict failure early (B) → intervene (A) → causally verify the intervention recovered the run (A).* A complete
arc: prediction → action → causal verification. B truncates and featurizes the *same* traces A replays, so they
share all infrastructure.

---

## 3. Study 2 — `paper-toolseo` (Idea C): *Tool descriptions as an adversarial surface*

**Central claim.** Holding tool capability *identical*, a meaningful share of tool-selection can be captured by
optimizing description text alone; the hijack persists after the inferior tool visibly fails; and only
outcome-based defenses generalize.

**Research questions.**
- RQ1 — Holding capability identical, how much selection share can description text buy (the *routing hijack rate*)?
- RQ2 — How does hijack scale with number of competing tools, and across backbones?
- RQ3 — Does hijacking *persist* after the inferior tool visibly fails — does the agent learn?
- RQ4 — What defenses work (capability-grounded selection, execution-outcome reputation, description normalization),
  and at what accuracy/latency cost?

**Three-act structure.**
- Act 1 (attack) — a synthetic registry of *matched tool pairs* (same underlying function; one honest description,
  one adversarially optimized). Optimizer is a DSPy program maximizing selection probability.
- Act 2 (measurement) — hijack rate across backbones and competitor counts, including a *malicious* variant where an
  inferior/harmful tool wins routing via description alone (the security stinger).
- Act 3 (defense) — propose and evaluate mitigations; show the trade-off curve.

**Hypotheses.**
- H1 — Can move selection by 20+ points on capability-identical tools with text alone.
- H2 — Hijack worsens as competitor count grows.
- H3 — Agents mostly **don't** learn from a well-described tool failing; they re-select it.
- H4 — Outcome-based reputation is the only defense that generalizes; pure text normalization is beaten by a better attacker.

**Baselines / comparisons.** honest-description routing, random routing, retrieval-based (Tool-RAG) routing — and
show Tool-RAG *doesn't* fix this because retrieval also runs on description text.

**Metrics.** routing hijack rate, selection-share delta, hijack-persistence-after-failure, attack-success under each
defense, defense cost (accuracy/latency/token overhead).

**Headline figure.** Hijack-rate plot (selection-share delta vs competitor count / across backbones).

**Ethics constraint (CLAUDE.md rule 6).** The attack optimizer is never open-sourced without its paired defense;
attack and defense ship in the same release.

---

## 4. Dependency order — why `paper-recovery` goes first

1. **It's the human's safest strong bet and it continues ARIA.** Existing skills and some code transfer; the
   "detection is not repair" finding corrects a field-wide assumption.
2. **It exercises the full shared harness.** Recovery needs the trace recorder, the replay layer, the tool
   sandbox, *and* the metrics module. ToolSEO needs a subset (sandbox + recorder + a selection metric, no replay).
   Building for the harder consumer first means ToolSEO reuses a proven core rather than co-evolving two half-built
   systems.
3. **A and B are internally ordered too:** A's replay harness produces the labeled per-step traces that B
   truncates and featurizes. So the true build order inside the study is *A's recorder/replay → collect traces →
   B's predictor*. But the **kill test for A** comes before either (see §6).
4. **ToolSEO is deliberately second, not concurrent.** One backbone, one scaffold, sequential focused studies
   (CLAUDE.md §6). Running both at once is the scope creep the operating manual warns against.

```
Shared harness (built for Recovery's needs)
        │
        ▼
 paper-recovery  ── Idea A (replay + interventions) ──▶ traces ──▶ Idea B (predictor + Pareto)
        │
        ▼  (harness now proven; reuse subset)
 paper-toolseo   ── Idea C (registry + DSPy attacker + defenses)
```

---

## 5. Shared harness components and who uses what

| Component | What it is | Recovery (A) | Recovery (B) | ToolSEO (C) |
|---|---|---|---|---|
| **Tool sandbox** | Registers instrumented tools; runs the agent scaffold against a task; deterministic tool effects with ground truth. | ✅ | — (consumes A's traces) | ✅ (registry of matched pairs) |
| **Trace recorder** | Per step: tool called, args, result, timestamp, monotonic step index → JSONL. | ✅ | ✅ (reads traces) | ✅ (records selections) |
| **Replay layer** | Reconstruct state up to step *k*, apply an intervention, resume forward. | ✅ (core) | — | ❌ (not needed) |
| **Metrics module** | Recovery rate, iatrogenic rate, cost; later Pareto + AUROC; later hijack rate. | ✅ | ✅ | ✅ (different metrics) |
| **Predictor / featurizer** | Truncate + featurize partial trajectory; train lightweight model; cost-model + threshold sweep. | — | ✅ | ❌ |
| **DSPy attacker** | Optimizes a description to maximize selection probability. | ❌ | ❌ | ✅ |
| **Defenses** | Capability-grounded selection, outcome reputation, description normalization. | ❌ | ❌ | ✅ |
| **Plotting** | Recovery matrix / Pareto curve / hijack-rate plot. | ✅ | ✅ | ✅ |

**Build-once core:** tool sandbox + trace recorder + replay layer + metrics module. Everything else is
study-specific and layered on top. The harness serves these experiments only — it is **not** a framework
(CLAUDE.md §6).

---

## 6. Kill tests — the cheapest experiment that could disprove each central hypothesis

Per CLAUDE.md §6 and research plan §4.1, each study starts here, **before** the full harness.

### 6.1 Recovery (A) kill test
- **Setup.** ~30 failing traces with ground truth. Hand-implement **3** interventions at the detected failure
  step (candidate set: reflect-and-retry, rollback-2, requirement-injection — final 3 are a design choice for you,
  §8). Replay each; count recoveries against ground truth.
- **Positive result (→ build the study):** recovery rates **differ sharply across failure classes** — at minimum
  one class where an intervention clearly helps and one where reflect-and-retry is flat or net-harmful (a visible
  iatrogenic case). This is the signal that a *matrix* exists to be filled.
- **Null result (→ pivot / stop):** all interventions recover at roughly the same rate across all failure classes
  (no cell structure). If intervention doesn't interact with failure class, there is no recovery matrix and the
  paper's premise is dead.
- **Provenance (DECIDED, §8 item 1).** ~30 failing traces are **generated fresh on the pinned Ollama model**
  (Option C) so record and replay share one backbone. Requires a minimal Ollama runner+recorder first. Each trace
  is then human-labeled with ARIA's decision tree, recording **both** its failure class **and** its oracle failure
  step *k* (§8 item 2). Ground truth is a deterministic per-task verifier → `answer_correct` boolean (§8 item 4).

### 6.2 Predictive early-stopping (B) kill test
- *B does not get an independent kill test before A.* B's whole premise ("failure is predictable early") is only
  worth testing once A has produced labeled per-step traces. The cheapest B-specific probe, once traces exist:
  truncate at an early step, fit a trivial predictor (drift + repetition + error density only), and check whether
  AUROC beats a length-only heuristic for **at least one** failure family.
- **Positive:** early AUROC clearly > length-only baseline for loop-type failures.
- **Null:** partial-trajectory features add nothing over length — no predictive signal early, so no Pareto story.

### 6.3 ToolSEO (C) kill test
- **Setup.** 10 matched tool pairs (identical capability). Optimize one description in each with a simple LLM/DSPy
  loop. Measure selection-share shift on the single Ollama backbone (extend to a second backbone only if you later
  approve one).
- **Positive result (→ build the study):** selection can be moved **20+ points** on capability-identical tools by
  description text alone (matches the human's H1 threshold).
- **Null result (→ pivot):** selection share barely moves (< ~20 points, or within noise). If text can't buy
  routing when capability is held identical, there is no adversarial surface to study.

Each kill test gets a one-page memo written **regardless of outcome** (research plan §4.1); that memo seeds the
paper intro and a `LOGBOOK.md` entry.

---

## 7. Timeline — solo, part-time

Assumes ~one focused person, part-time (evenings/weekends, call it ~10–15 hrs/week), local Ollama only, and that
GATE approvals are reasonably prompt. Ranges are deliberate; research slips.

| Weeks | Phase | Deliverable |
|---|---|---|
| **0** | Setup & alignment | Ollama up, venv, deps pinned, repo scaffolded, GATEs 1–3 cleared. |
| **1–2** | Recovery **kill test (A)** | 3 hand-coded interventions on ~30 traces; recovery-differs-by-class memo. **Go/pivot decision.** |
| **2–4** | Shared harness | Tool sandbox, trace recorder, replay layer, metrics module — with pytest tests. |
| **4–6** | Recovery full matrix (A) | All 8 interventions × 5 failure classes; recovery matrix figure; baselines; iatrogenic + cost metrics. |
| **6–7** | Predictor (B) | Truncate/featurize A's traces; train predictor; sweep threshold → Pareto frontier. |
| **7–8** | Recovery analysis | Robustness (lateness curve, policy vs 4 baselines); honest write-up of A+B; workshop draft. |
| **8–9** | ToolSEO **kill test (C)** | 10 matched pairs; DSPy/LLM description optimizer; 20-point check. **Go/pivot decision.** |
| **9–11** | ToolSEO attack + measurement | Synthetic registry; hijack rate vs competitor count; malicious variant. |
| **11–13** | ToolSEO defenses + analysis | Capability-grounded / outcome-reputation / normalization defenses; trade-off curves; hijack-rate figure. |
| **13–15** | Write-up buffer | Both papers to workshop-submittable; limitations; related work; slack for slippage. |

Milestones that gate everything after them: **kill-test A (wk 2)** and **kill-test C (wk 9)**. A null at either
changes the plan — that's the point of running them first.

---

## 8. Design decisions I believe are yours, not mine

These touch experimental validity, so per CLAUDE.md §2 I will **not** decide them silently. I need your calls
(some block specific phases; noted):

1. **Trace data provenance for Recovery (blocks kill test A).** — **DECIDED (2026-07-21): Option C — generate
   fresh failing traces on the pinned Ollama model.** Rationale (human's): a clean single-backbone counterfactual
   (record and replay share one model), no dependency on recovering ARIA's gitignored trace set, and the Ollama
   runner+recorder is on the critical path regardless. Option B (reuse ARIA + relabel) is **skipped entirely** to
   avoid carrying the Groq→Ollama confound. Consequence: a minimal Ollama runner+recorder must exist before the
   kill test can produce traces (still lighter than the full harness).
2. **Failure-class definitions and labeling protocol.** — **DECIDED (2026-07-21): adopt ARIA's
   `docs/labeling-guide.md` verbatim, including ARIA's exact class names.** Matrix rows are renamed to ARIA's
   vocabulary: `prompt_drift`, `tool_misuse`, `context_overflow`, `hallucination_loop`, `goal_misalignment`
   (+ `none`, and meta-labels `gap`/`multi`/`unclear`). **Labeling rule:** single labeler following ARIA's written
   decision tree at kill-test scale; restore ARIA's two-annotator + Cohen's κ protocol for the full study.
   **ADDITION (human):** because detection-step *k* is oracle-labeled (item 5), the labeling pass must record, per
   trace, **both** the failure class **and** the failure step *k*. This goes into the rubric used for our traces.
3. **The 3 interventions for kill test A.** — **DECIDED (2026-07-21):** reflect-and-retry (incumbent under test),
   rollback-2, requirement-injection.
4. **Ground-truth definition per task.** — **DECIDED (2026-07-21): per-task-type deterministic verifier, each
   reduced to a single `answer_correct` boolean.** Numeric/canonical → normalized exact-match; open-domain QA →
   fact-match (normalized match / F1); file/deliverable tasks → file-existence + content check; tool/transaction
   tasks → environment-state check. **Hard constraint (human): every verifier is deterministic — never an LLM
   judge.**
5. **"Detection at step *k*" — where does *k* come from in the kill test?** — **DECIDED (2026-07-21):** use the
   oracle-labeled failure step for the kill test (decouples detection from repair).
6. **Cost model(s) for Idea B's Pareto.** The token/latency/stakes cost structure defines the frontier's shape and
   which regimes "early abort dominates." This is an economics-of-the-result decision.
7. **The agent scaffold to pin.** One scaffold, per CLAUDE.md. Which one (e.g., a ReAct-style loop, or a specific
   library)? Affects reproducibility and what "a step" means.
8. **The single Ollama model to pin.** — **DECIDED (2026-07-21): `qwen2.5:7b`.** Chosen after a head-to-head
   tool-calling smoke test on the human's hardware: qwen2.5:7b produced clean multi-step tool chaining 6/6 (both
   feedback regimes), whereas llama3.1:8b failed argument-threading on the 2nd step 100% of the time (0/6 clean).
   qwen2.5:7b gives a controllable trace substrate; the cost (dropping ARIA model-family continuity) is minor since
   provenance is Option C (fresh traces). Lighter fallback if memory-tight: `llama3.2:3b`.
9. **ToolSEO capability-identical guarantee.** How we *prove* two tools have identical capability (same code path?
   same outputs on a test battery?) — this is the confound that the entire study rests on. Your call on the standard.
10. **Statistical plan (replay determinism/sampling).** — **DECIDED (2026-07-21): Option (b) — sample N replays
    per (intervention, trace) and report a recovery-rate DISTRIBUTION, not a single sample.** N is config-switchable
    (default **3** for real runs; **N=1** allowed for fast iteration). **N=3 is a floor, not a ceiling** — the
    metrics module must support raising N per-cell where a recovery rate sits near a decision boundary. **Every
    replay logs seed, temperature, and model tag.** (Remaining sub-question still open: significance test / CI
    method for comparing cells — to be settled once the kill test shows the effect size.)

I'll bring 1–5 to you again at the Recovery kill-test gate (they block it), and 6–10 as their phases approach.

---

*End of work plan. Awaiting GATE 1 approval before any further action.*
