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

## Verdict

**The recovery premise is confirmed on qwen at real n, with a corrected mechanism.** Skipped-lookup
hallucination is recoverable specifically by repairs that **license the corrective action** (recovery up
to 1.00), the DR-4 imperative/declarative story is refuted and replaced by action-licensing, detection
lateness degrades recovery, and **surface-form (tool-false-validated) misuse resists all text repairs**.
These are the two headline results the paper is built on, now on real-n directional data with the earlier
hypothesis honestly corrected. Next: (1) raise N on the near-boundary mid-range cells; (2) the
**second-backbone generalization check** is now sequenceable (recovery signal confirmed on qwen) — replicate
"action-licensing recovers skipped-lookup" and "surface-form misuse is recovery-resistant" on a second model.
