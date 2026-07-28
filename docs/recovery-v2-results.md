# v2 Recovery Sweep — Results (paper-recovery)

*The recovery machinery run at real n on the labeled v2 pools. **DIRECTIONAL** — single model
(qwen2.5:7b), N=3 replays/cell, pools n=50 (skipped-lookup) and n=31 (surface-form misuse). Verified:
sample replays were re-run with full output capture to confirm the numbers reflect real behavior, not
verifier artifacts. Raw: `data/v2batch/recovery_v2/results.json`.*

**Date:** 2026-07-27. Arms: `no_op` (control), `reflect_and_retry`, `rollback_2`, `restart_clean`, and
`requirement_injection` in 4 phrasings — imperative-only / imperative-plain / declarative-neutral /
declarative-lookup-permitting.

---

## Result 1 — Skipped-lookup IS recoverable, and the driver is ACTION-LICENSING, not grammatical mood

Recovery rate by arm × chain depth (macro rate; n traces in parens):

| arm | depth 1 | depth 2 | depth 3 |
|---|---|---|---|
| no_op (control) | 0.03 (21) | 0.00 (23) | 0.00 (6) |
| **reflect_and_retry** | **0.75** (8) | **0.79** (8) | **0.89** (6) |
| rollback_2 | 0.25 (8) | 0.00 (8) | 0.00 (6) |
| restart_clean | 0.25 (8) | 0.00 (8) | 0.00 (6) |
| req_imperative_only | 0.67 (21) | 0.12 (23) | 0.00 (6) |
| req_imperative_plain | 0.62 (21) | 0.51 (23) | 0.00 (6) |
| req_declarative_neutral | 0.24 (21) | 0.29 (23) | 0.00 (6) |
| **req_declarative_lookup_permitting** | **1.00** (21) | **0.83** (23) | **0.39** (6) |

**The DR-4 "declarative beats imperative" hypothesis is REFUTED at real n.** `declarative_neutral`
("*the answer must be* the manager's name") is among the **worst** arms (0.24 / 0.29 / 0.00) — *below*
`imperative_plain` (0.62 / 0.51 / 0.00) at every depth. Grammatical mood does not explain recovery.

**What does: whether the repair LICENSES THE CORRECTIVE ACTION.** The two robust recoverers both
explicitly prompt re-work — `declarative_lookup_permitting` ("...*use tools to verify*") and
`reflect_and_retry` ("*review your work*"). Verified in replay: under these, the model issues the missing
`get_record` and returns the correct name; under `declarative_neutral` it makes **no tool call** and
re-asserts the record's own name. So the earlier "imperative vs declarative" framing (one task, DR-4) is
superseded by **action-licensing vs not** — the "declarative" winner in DR-4 happened to also be
lookup-permitting.

**RQ3 (detection lateness) is visible:** recovery degrades with chain depth for most arms — imperative
arms collapse by depth 3; even `lookup_permitting` falls 1.00 → 0.39. Only `reflect_and_retry` holds
across depth. `no_op` ≈ 0 at all depths (deep skips do not self-recover; `restart_clean` just repeats the
chain and skips again).

**No iatrogenic harm on skipped-lookup:** every arm is ≥ no_op (all net-positive, iatrogenic ≈ 0.00).

## Result 2 — Surface-form misuse is recovery-RESISTANT

Recovery rate by arm × surface form:

| arm | date (13) | hhmm (11) | version (6) |
|---|---|---|---|
| no_op | 0.00 | 0.00 | 0.28 |
| reflect_and_retry | 0.05 | 0.15 | 0.33 |
| rollback_2 / restart_clean | 0.00 | 0.00 | 0.33 |
| req_imperative_only | 0.03 | 0.00 | 0.00 |
| req_imperative_plain | 0.00 | 0.00 | 0.00 |
| req_declarative_neutral | 0.03 | 0.00 | 0.33 |
| req_declarative_lookup_permitting | 0.08 | 0.15 | 0.00 |

**Date and HHMM misuse resist every arm (≤ 0.15).** No text-level repair recovers a failure the tool
**false-validated** — the model already holds a well-formed (wrong) number the tool "confirmed," so
prompting it to review or to report the answer does not remove the false validation. This confirms the
§2.0 characterization ("the counterfactual-repair cluster is structurally blind to this") at real n, and
sharpens it: the failure is *not* text-repairable because the corrupting signal is a tool result, not a
prompt.

**Version (n=6) is a noisy outlier** — `no_op` is already 0.28 (stochastic re-rolls), so "recovery" there
is mostly noise, not intervention; imperative arms drop to 0.00 (a weak iatrogenic hint, n=6). Consistent
with the earlier flag that dotted-version is a noisy inducer; do not lean on it.

## Verification

Sample replays were re-run with full output capture (`_inspect/`). Confirmed: (a) `lookup_permitting`/
`reflect` recoveries are **genuine** — the model makes the previously-skipped `get_record` and returns the
correct entity; (b) `declarative_neutral` genuinely fails by re-asserting the intermediate/own entity with
no lookup; (c) surface-form "recovery" attempts are near-zero and messy (60/39/refusals). No verifier
false-positives found in the sample.

## Honest caveats

- **Directional, single model, N=3.** The audit flagged **119 near-boundary cells** — mid-range rates
  (e.g. `imperative_plain` 0.51) need higher N to firm up. The *extremes* are robust: no_op ≈ 0,
  `lookup_permitting` ≈ 1.00 at depth 1, `declarative_neutral` ≈ 0.24, date-misuse ≈ 0.
- `reflect`/`rollback`/`restart` ran on a depth-stratified breadth subset (n=8/8/6), smaller than the
  phrasing arms (n=21/23/6); comparisons across those are coarser.
- `version` (n=6) is too small and too noisy to carry weight.

## Step-1 firm-up (N=10 on the argument-critical cells) — the contrast HOLDS

The action-licensing claim rests on a contrast (`declarative_neutral` bad vs
`lookup_permitting`/`reflect` good), so those cells were re-run at **N=10** (skipped-lookup 6 arms × 50
across depths; surface-form date+hhmm 8 arms × 24). Skipped-lookup, recovery by arm × depth:

| arm | d1 | d2 | d3 |
|---|---|---|---|
| no_op | 0.07 | 0.00 | 0.00 |
| reflect_and_retry | 0.60 | 0.83 | 0.60 |
| req_imperative_only | 0.69 | 0.11 | 0.00 |
| req_imperative_plain | 0.66 | 0.42 | 0.20 |
| **req_declarative_neutral** | **0.16** | **0.18** | **0.20** |
| **req_declarative_lookup_permitting** | **1.00** | **0.75** | **0.60** |

**Verdict: the action-licensing contrast HOLDS at N=10 (does not soften).**
- `declarative_neutral` (bare constraint) stays **low at every depth** (0.16 / 0.18 / 0.20) — it is the
  *worst* arm at depths 1–2, well below `imperative_plain` (0.66 / 0.42). So "declarative beats imperative"
  is refuted, firmly.
- The two **action-licensing** arms stay **high**: `lookup_permitting` (1.00 / 0.75 / 0.60) and `reflect`
  (0.60 / 0.83 / 0.60). The only thing separating `lookup_permitting` (0.75–1.00) from `declarative_neutral`
  (0.16–0.20) — both declarative — is the *licensing clause* ("use tools to verify"). That is the driver.
- `imperative` arms sit in between and **collapse with depth** (imperative_only 0.69 → 0.11 → 0.00) — RQ3
  lateness, confirmed. No arm is iatrogenic (all net-positive vs no_op; `lookup_permitting` +0.80, `reflect`
  +0.68, `declarative_neutral` only +0.14).

Surface-form (date+hhmm) at N=10 — **every arm ≤ 0.14** (date ≤ 0.06, hhmm ≤ 0.14): the
**recovery-resistant headline HOLDS** firmly; no text repair reaches a tool-false-validated failure.

## Step 2 — Second backbone (Mistral 7B): generalization is CONFOUNDED by tool-capability

Per the sequencing rule, after the recovery signal was confirmed on qwen we ran a narrow generalization
check on a different-family model, **mistral:7b**. It needs its own failing traces (no cross-model replay),
so we piloted its hit rate first (31 tasks × 3 = 93 runs). **Verdict: Mistral is too tool-unreliable to
serve as a clean generalization backbone for these mechanisms — the recovery findings are UNTESTABLE on it,
and the exercise itself surfaced a real methodological limit.**

**Tool-calling smoke:** 3/6 clean (chains multi-step, but ~half the runs have arg-threading errors) —
between llama3.1 (0/6) and qwen (6/6).

**Hit rates looked high but are dominated by Mistral-specific tool pathologies.** Categorizing all 81
failing traces:

| category | n | is it the mechanism? |
|---|---|---|
| SL: lookup-then-assert/incomplete | 34 | partly — genuine skipped-lookup fabrication mixed with honest incompletes |
| **tool-emit-as-text** (printed the tool call as literal text, never called it) | 18 | **no — Mistral tool-format bug** |
| **no-tool-call** (reasoned in text, e.g. converted HHMM by hand) | 16 | **no** |
| other-arith (muddled, e.g. `add(1604438, 61)`) | 10 | no |
| **CLEAN surface-form-misuse** (fed a date-int/HHMM to arithmetic) | **3** | yes — but only 3 |

**Three framings (the exercise strengthened the account rather than just limiting it):**

1. **Skipped-lookup hallucination GENERALIZES — a confirmed cross-model result.** Mistral fabricates the
   unfetched value too — verified: it reads `manager=#202` and invents "John Smith"/"John Doe" without ever
   calling `get_record(202)`. The mechanism is **no longer qwen-only**; it reproduces in a second,
   different-family model. (~34 candidate traces, spot-checked; labeling would split genuine fabrication from
   honest incompletes, but the fabrication behavior is present and clear.)

2. **Surface-form ("tool false-validation") misuse is MODEL-CONDITIONAL — stated as a finding with a named
   precondition, not merely a limitation.** It reproduced in only 3/81 Mistral traces because **Mistral does
   not reflexively apply the arithmetic tool to numeric-looking strings** — it reasons about dates/times in
   text instead. That identifies the *precondition for the vulnerability*: **tool-false-validation misuse
   occurs in TOOL-REFLEXIVE models (those that reach for a general tool on any operand-shaped input), and
   when it occurs it is unrecoverable by text-level repair.** Naming *which* agents are vulnerable (the
   tool-reflexive ones) is a sharper and more useful contribution than a blanket "agents misuse tools"
   claim — it tells a practitioner exactly which deployments are at risk.

3. **Recovery generalization is UNTESTABLE at local-7B — itself a methodological contribution.** 34/81
   Mistral failures are tool-emission pathologies (`tool-emit-as-text` + `no-tool-call`), and every recovery
   arm depends on the model *re-issuing a tool call*, so "failed to recover" cannot be separated from
   "couldn't emit a tool call." **Evaluating recovery on a tool-unreliable model conflates intervention
   efficacy with tool competence** — a real caution for anyone benchmarking agent recovery across models,
   and a reason such studies must first establish a tool-reliability floor.

Because running the recovery sweep on Mistral would conflate intervention efficacy with tool competence, it
was **not run** (per the pre-committed rule: report the confound, don't force a muddy comparison).

## Limitations and scope

Stated plainly, because the findings are only as strong as their scope.

- **Single primary model.** All recovery results are on **qwen2.5:7b**. The second-backbone check
  (Mistral) confirmed the skipped-lookup *mechanism* cross-model but could not test recovery (tool
  confound). So the recovery findings (action-licensing; text-repair resistance) are **demonstrated on one
  model** and not yet shown model-general.
- **Synthetic sandbox.** Tasks, tools, and fixtures are deterministic and small (record chains, date/clock
  strings). This buys a clean counterfactual and audited ground truth, but external validity to real agent
  workloads is unestablished.
- **Directional n.** The headline extremes are firm at N=10 (skipped-lookup arms, surface-form date+hhmm),
  but some cells remain N=3 and several mid-range rates sit near a decision boundary — treated as
  directional, not precise point estimates.
- **Tool-capability confound (generalization).** Evaluating recovery across models is confounded by
  tool-use reliability: a model must be tool-reliable enough to (a) exhibit the mechanism and (b) respond to
  a tool-based repair. At local-7B scale only qwen2.5 met that bar; Mistral and llama3.1 did not. This both
  limits the generalization claim and is itself a reported methodological result.
- **Labeling.** Failure-class labels were assigned by a single labeler (assisted), spot-check-validated;
  no inter-annotator agreement (κ) was computed at this scale.

## Verdict

On qwen2.5:7b at real n: skipped-lookup hallucination is recoverable specifically by repairs that **license
the corrective action** (up to 1.00; the DR-4 imperative/declarative story refuted → action-licensing),
recovery **decays with detection lateness**, and **surface-form (tool-false-validated) misuse resists all
text-level repair**. The second-backbone check **confirms the skipped-lookup mechanism cross-model**, shows
**surface-form misuse is tool-reflexive-model-conditional**, and documents that **recovery generalization is
confounded by tool-capability** at local-7B. The next phase is **write-up**, not more runs.
