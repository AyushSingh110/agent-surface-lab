# Phase 4 — Provenance kill test (SPEC ONLY, nothing built)

*A proposal for the human's approval. No code, no fixtures, no runs. Per CLAUDE.md §6, the first thing built
for a new study is the cheapest experiment that could **disprove** the central hypothesis — not the harness.*

---

## 1. Where this hypothesis came from (it is already half-observed)

LOGBOOK 2026-07-25, buried in the ambiguous-group scoring audit:

> **the misuse fires when the date ARRIVES AS A TOOL RESULT, not when stated in the prompt** — SM depth-1
> (dates via `kv_lookup`) CLEAN 12/12; SM depth-0 (dates stated in the prompt, SM-02/03/04) collapses into
> refusals and reflection.

Same content. Different delivery channel. Opposite behaviour, 12/12 versus ~0. That was a **byproduct** of a
task-design axis, not a controlled comparison — which is exactly why it needs its own kill test rather than
a citation.

## 2. The hypothesis

> **H-PROV: An agent assigns epistemic status by the CHANNEL a fact arrived on, not by the fact's content.**

Concretely: identical information delivered as a tool result versus stated in the prompt produces different
rates of verification, acceptance, and downstream use.

**Why it matters.** The prompt-injection literature measures *attacks succeeding*. It has never established
the **base-rate trust ordering over channels** that makes those attacks work. If channel provenance
systematically outranks content, that is the substrate the entire field assumes but has not quantified — and
it tells a practitioner exactly which channel needs the guardrail.

**Why it fits this program.** Provenance is the purest possible surface cue: content is held *byte-identical*
and only the delivery route varies.

## 3. The kill test (cheap, ~2 days, no new harness)

**Design.** Take N=8 facts. Deliver each through two channels, content byte-identical:

- **(A) prompt-stated** — the fact appears in the user instruction
- **(B) tool-returned** — the fact arrives as the return value of a `lookup` tool

Then ask a question whose correct answer requires the agent to *check* that fact against a second source
that **contradicts** it.

**Primary measure — verification rate.** Does the agent issue a second tool call to confirm the fact before
using it? One deterministic boolean per run: was the corroborating tool called?

**Secondary measure — conflict resolution.** When channel A says X and channel B says ¬X, which wins? A
deterministic check of which value appears in the final answer.

**Cost.** 8 facts × 2 channels × N=10 replays = **160 runs**. One evening on the existing runner. No new
verifier machinery: "was tool T called" and "which of two known values was reported" are both deterministic
and immune to the string-matching failure modes that bit us three times in v1.

## 4. Pre-committed kill criteria (set BEFORE running)

| Outcome | Verdict |
|---|---|
| Verification-rate gap between channels **< 0.15** with a CI containing zero | **HYPOTHESIS DEAD.** Report the null, do not build the full study. |
| Gap **≥ 0.15**, CI excludes zero | Proceed to the full factorial |
| Conflict resolution is ~50/50 | Channel does not dominate; report as a weaker result |

Stating these now so the threshold cannot drift after seeing results — the same discipline used for the
Phase 3 screening bar.

## 5. If it survives — the full study (NOT approved, sketch only)

Five channels, content constant: system prompt · user prompt · authoritative-named tool (`get_record`) ·
low-trust-named tool (`scrape_web`) · retrieved document blob. Measures: verification rate per channel, and a
**measured trust ordering** from pairwise conflicts.

The `get_record` vs `scrape_web` pair is the sharpest cell: **identical mechanism, identical return, different
name.** If trust tracks the tool's *name*, that is the surface-cue thesis proven at its cleanest.

## 6. Honest risks

- **The qwen2.5-only constraint applies here too.** Phase 3 established that only one local model chains
  reliably, so this will also be single-model. Provenance effects may be more model-general than recovery
  effects, but that is an assumption, not evidence.
- **The depth-0/depth-1 observation is confounded.** Those tasks differed in chain depth *and* channel
  simultaneously. The kill test must hold depth fixed and vary only channel, or it reproduces the confound
  that made C2 need a factorial.
- **A null is a real possibility** and would be worth reporting: "agents do *not* discriminate by provenance"
  is a useful finding for the injection literature, which largely assumes they do.
- **Contradiction may trigger refusal** rather than verification (v1 saw the model refuse rather than
  fabricate). The scoring must treat refusal as its own category, not silently as failure.

## 7. What I need before building anything

1. Approve or revise **H-PROV** as stated.
2. Approve the **kill criteria** in §4 — especially the 0.15 threshold.
3. Confirm the **verification-rate** primary measure (vs. making conflict-resolution primary).
4. Confirm scope: kill test **only**, then stop and report.

*Nothing will be built until these are settled.*
