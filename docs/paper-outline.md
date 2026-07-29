# Paper Skeleton — paper-recovery

*Outline only, for review of the claim→evidence mapping BEFORE any writing. Nothing here is prose to keep;
it exists so the human can see exactly how solid each load-bearing sentence is. All recovery numbers are on
`qwen2.5:7b` (primary); Mistral is the cross-model probe. Evidence lives in `docs/recovery-v2-results.md`
and `data/v2batch/*` / `data/mistral_pilot/*`.*

---

## Working title (options)

1. **"Not All Repair Helps: Which Interventions Recover a Failing Tool-Agent, and Which Cannot Reach It."**
2. "Action-Licensing, Not Mood: How the Surface Form of a Repair Decides Whether a Tool-Agent Recovers."
3. "Two Failure Mechanisms of Capable Tool-Agents, and the Limits of Text-Level Repair."

*(Lead with #1 or #2; both foreground the recovery result. #2 foregrounds the sharpest single finding.)*

## One-paragraph abstract sketch

A capable instruction-tuned tool-agent rarely loops or skips deliverables; on a controlled sandbox it fails
in two reproducible ways — **fabricating a fact that was available but unfetched (skipped-lookup)** and
**misusing a working tool whose non-error result falsely validates a meaningless computation
(tool-false-validation)**. We measure repair **causally, by counterfactual replay against a no-op control**,
and find: (i) skipped-lookup is recoverable, but by repairs that **license the corrective action**, not by
grammatical mood — an identical requirement recovers 1.00 or 0.16 depending on whether it permits the fix;
(ii) tool-false-validation misuse is **unrecoverable by any text-level repair**, because the corrupting
signal is a tool result, not a prompt. We contribute the mechanism as a **taxonomy gap** the
counterfactual-repair literature is structurally blind to, a **detection-lateness** result, and a
**methodological caution**: cross-model recovery evaluation is confounded by tool-capability.

## Contributions (claim list)

- **C1** A two-mechanism characterization of how a capable tool-agent fails (skipped-lookup; tool-false-validation).
- **C2** *Action-licensing* recovers skipped-lookup; grammatical mood does not (correcting a prior hypothesis).
- **C3** Tool-false-validation misuse is unrecoverable by text-level repair, and is model-conditional (precondition: tool-reflexivity).
- **C4** *Silent tool misuse* as a taxonomy gap the DoVer/CausalFlow/CAR cluster cannot detect.
- **C5** Detection-lateness degrades recovery (chain depth).
- **C6** Methodological: cross-model recovery evaluation is confounded by tool-capability; and an adversarial verifier-audit protocol.

---

## Section skeleton

1. **Introduction** — the on-call question ("it's failing; do I intervene, and will it help or hurt?"); the
   surface-cue thesis; contributions C1–C6.
2. **Related work** — attribution saturation (Who&When/Pro, AgenTracer, GraphTracer); the counterfactual-
   repair cluster (DoVer, CausalFlow, CAR) and *what it does not measure* (iatrogenic rate; no-op control;
   and — C4 — failures with no error signal); ARIA taxonomy lineage. *Honest positioning:* we do NOT claim
   "intervene-and-verify" as novel (scooped); we claim the class/mechanism-conditional accounting + the gap.
3. **Method** — harness (recorder, replay+`reconstruct`, interventions incl. no-op control); **deterministic
   verifiers + adversarial audit** (false positives as the dangerous direction); task families (skipped-
   lookup depths 1–3; surface-form date/HHMM/version) with selectivity controls; labeling protocol;
   determinism policy (N replays; per-cell distribution).
4. **The failure surface** (C1) — Table 1.
5. **Recovering skipped-lookup: action-licensing** (C2) — Table 2 + Figure 1.
6. **Detection lateness** (C5) — Figure 1 (depth axis).
7. **Tool-false-validation misuse is unrecoverable and model-conditional** (C3, C4) — Table 3, Table 4.
8. **Cross-model generalization and the tool-capability confound** (C6) — Table 4, Table 5.
9. **Limitations and scope** — verbatim from `recovery-v2-results.md`.
10. **Conclusion.**

## Figures / tables (the evidence artifacts)

- **Table 1** — failure-mode incidence by mechanism × trigger-depth (v2 hit rates, qwen). Source: `data/v2batch` pilot.
- **Table 2** — recovery rate, arm × depth, skipped-lookup, **N=10** (headline). Source: `recovery_firm/results.json`.
- **Figure 1** — recovery vs chain depth, per arm (the lateness curve; also carries C2's contrast visually).
- **Table 3** — recovery rate, arm × surface-form (date/hhmm), **N=10** (headline negative). Source: `recovery_firm`.
- **Table 4** — Mistral failing-trace categorization (81 traces): mechanism vs tool-emission pathology.
- **Table 5** — tool-calling reliability by model (smoke): llama3.1 0/6, mistral 3/6, qwen 6/6.
- **Table 0 (appendix)** — verifier adversarial battery: #cases, #known residual gaps (method credibility).

---

## CLAIM → EVIDENCE MAP (read this first)

Solidity key: **STRONG** = N=10, robust at the extremes · **MODERATE** = clear trend but small-n or 2-model
· **SINGLE-MODEL** = recovery result on qwen only · **INTERPRETIVE** = mechanism story on top of data ·
**NEAR-BOUNDARY** = depends on mid-range N=3 rates (NOT used in any headline).

| # | Load-bearing sentence | Evidence | Solidity / flags |
|---|---|---|---|
| C1a | The model rarely loops / skips deliverables / misuses *erroring* tools | v1 pilots (n=20/84), v2 controls | MODERATE · single-model · small-n on v1 |
| C1b | It fails via skipped-lookup and tool-false-validation | Table 1; labeled v2 pools (SL n=50, SF n=31) | MODERATE→STRONG · single-model |
| **C2** | Skipped-lookup is recovered by **action-licensing** repairs, not grammatical mood | **Table 2 (N=10)**: `declarative_neutral` 0.16/0.18/0.20 vs `lookup_permitting` 1.00/0.75/0.60; two declaratives differ only by the licensing clause | **STRONG** within-model · **SINGLE-MODEL** |
| C2-corr | This *corrects* the earlier "imperative vs declarative" hypothesis | §4.8→§4.10 + LOGBOOK (documented retraction) | STRONG (honesty/provenance) |
| **C3a** | Tool-false-validation misuse is **unrecoverable by any text-level repair** | **Table 3 (N=10)**: all arms ≤0.14 on date+hhmm | **STRONG** within-model · **SINGLE-MODEL** |
| C3b | …because the corrupting signal is a **tool result, not a prompt** | Interpretation of Table 3 + replay traces | **INTERPRETIVE** (plausible, not directly tested) |
| C3c | Misuse is **model-conditional**: occurs in tool-reflexive models, not text-reasoning ones | Table 4 (Mistral 3/81 clean; reasons in text) vs qwen | MODERATE · 2-model |
| **C4** | *Silent tool misuse* is a taxonomy gap (not tool_misuse — no error; not hallucination_loop — real tool result); the repair cluster is structurally blind to it | §2.0 definition (crit. 1–4) + DR-6/SM examples; argument re DoVer/CausalFlow/CAR detectors | MODERATE · conceptual + qwen-grounded · **needs the "blind" claim stated as reasoned, not measured on their systems** |
| **C5** | Detection lateness degrades recovery (deeper skip → harder) | Table 2 / Figure 1: imperative 0.69→0.11→0.00; lookup_permitting 1.00→0.75→0.60; no_op ≈0 | MODERATE→STRONG · **depth-3 is n=6 (thin) — state the trend, not the point** |
| C6a | Skipped-lookup mechanism **generalizes** cross-model | Table 4: Mistral fabricates unfetched value ("John Smith" w/o get_record) | MODERATE · 2-model · Mistral pool noisy |
| **C6b** | Cross-model recovery eval is **confounded by tool-capability** | Table 4 (34/81 tool-emission pathologies) + Table 5 | STRONG (well-evidenced methodological point) |
| C6c | No repair arm is **iatrogenic** on skipped-lookup | iatrogenic table (all net-positive vs no_op) | MODERATE · single-model |
| M1 | Recovery measured causally (replay + no-op control), not LLM-judge | Method + harness code + tests | STRONG (design) |
| M2 | Verifiers are audited; false positives caught | Table 0; audit battery + `test_verifier_audit.py`; 3 documented retracted verifier bugs | STRONG (design/provenance) |

### Load-bearing sentences that currently rest on a soft number (flagged for the human)

- **Every recovery claim (C2, C3a, C5, C6c) is SINGLE-MODEL (qwen2.5:7b).** The paper's recovery story
  stands or falls on qwen; Mistral confirmed only the *mechanism*, not recovery. This is the biggest
  solidity gap and must be stated in the abstract, not buried.
- **C3b and C4's "blind" clause are INTERPRETIVE** — reasoned from the data and from the cluster's detector
  design, not measured on their systems. Frame as "we argue", not "we show".
- **C5 depth-3 (n=6) and the dotted-version sub-family (n=6) are thin** — report the trend; do not quote the
  point estimates as precise.
- **~119 near-boundary N=3 cells are NOT used in any headline** — headlines use the N=10 extremes only. Keep
  it that way; do not let a mid-range N=3 number become load-bearing.

---

## Target venues (shortlist — agentic-AI / reliability)

- **ICLR / NeurIPS workshops** on Agentic AI, LLM agents, or reliability (e.g. R0-FoMo-style) — the
  "detection is not repair / not all repair helps" negative-result framing fits workshop appetite; directional
  n is acceptable there.
- **ACL/EMNLP Findings or workshop** (agent evaluation / tool use) — the taxonomy-gap (C4) and the
  action-licensing surface-cue result (C2) suit an NLP-agent audience.
- **A short arXiv preprint** positioning the harness + audited-verifier methodology + honest negative results
  — the reusable-method angle is a strong standalone.
- *Reach (needs a second tool-reliable model, currently blocked):* a main-track reliability/MLSys submission
  — not advisable until the single-model constraint is relaxed.

## Honest venue read

This is a **workshop-tier** contribution as it stands: clean method, two real directional findings, a sharp
taxonomy-gap, and unusually honest limitations — but single-model recovery + synthetic sandbox cap it below
a main-track bar. The most durable contributions for citation are **C4 (taxonomy gap)** and **C6b
(tool-capability confound in recovery eval)**; C2 is the most quotable.

*No writing beyond this outline until the claim→evidence map is reviewed.*
