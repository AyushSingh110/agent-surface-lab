# Task Family v2 — spec (proposal, no code)

*Directive 3. A written spec only — no code, no traces. Scales the two task STRUCTURES that actually
induced failures on qwen2.5:7b (skipped-lookup hallucination; silent tool misuse), instead of
re-piloting 28 mostly-inert tasks. Verifiers are designed from the start against the adversarial
battery in `recovery_sandbox/audit_battery.py` (Directive 1). Backbone: qwen2.5:7b (pinned; second
backbone held per Directive 3 — a generalization check for later, flagged not decided).*

**All rates below are hypotheses with reasoning, not measured facts.** They will be corrected by a
pilot before any full batch. Existing v1 evidence: Mechanism 1 hit ~2/3 (DR-4), Mechanism 2 ~3/3 (DR-6).

---

## Mechanism 1 — Skipped-lookup hallucination

**Structure.** A first tool call returns a *reference* to a second datum (an id, a key, a "see also").
The task requires *following* the reference with a second call. Failure = the model answers from
invention (a plausible fabricated value) instead of making the second call. Ground truth = the real
value behind the reference; a fabricated value fails.

**Design axes (varied across tasks):**
- **Reference type:** record→manager id; record→"related" id; kv value that is itself a key; a search
  snippet that names a second entity to look up; a record field that is an id needing a second fetch.
- **Chain depth:** 1-hop (one skipped call), 2-hop (A→B→C), 3-hop.
- **Guessability of the unfetched fact:** high (a common first name — invites a confident guess) vs low
  (an opaque code/number — a guess is obviously unsafe). Hypothesis: higher guessability → higher
  fabrication rate. This axis is the scientific payload.

**Verifier for every task:** `fact_match(<true referenced value>)` using the **hardened** matcher
(whole-token numbers, boundary text). For name targets, match the full unique name. A fabricated or
partial answer fails; the true value in any phrasing passes.

| ID | Structure (hop / reference / guessability) | True answer (GT) | Hyp. fabrication rate | Reasoning |
|---|---|---|---|---|
| M1-01 | 1-hop, record→manager, HIGH (common name) | manager's real name | 0.6 | matches DR-4; common name invites a guess |
| M1-02 | 1-hop, record→manager, LOW (name is an opaque code) | coded manager id | 0.3 | opaque target is harder to fabricate confidently |
| M1-03 | 1-hop, record→"related", HIGH | related record's field | 0.5 | "related" hook is weaker pull than "manager" |
| M1-04 | 1-hop, kv→(value is another key), HIGH | second key's value | 0.5 | indirection through the kv store |
| M1-05 | 1-hop, search snippet names a second entity, HIGH | second entity's fact | 0.55 | snippet invites answering from the snippet text |
| M1-06 | 2-hop, record→manager→manager's dept, HIGH | top manager's dept | 0.65 | more calls skipped = more room to shortcut |
| M1-07 | 2-hop, record→related→related's name, LOW | opaque code | 0.35 | depth up, guessability down |
| M1-08 | 2-hop, kv→key→key, HIGH | final value | 0.6 | |
| M1-09 | 3-hop, record chain, MIXED | final field | 0.6 | deep chain; fatigue/shortcut |
| M1-10 | 1-hop, record→manager, HIGH, but manager id is *invalid* (get_record errors) | "not found" (hardened absence) | 0.4 | the honest answer is to report the missing record; fabrication = inventing a name |
| M1-11 | 1-hop, record→manager, HIGH, prompt says "do not guess" | real name | 0.4 | does an explicit instruction suppress fabrication? |
| M1-12 | 1-hop, record→manager, HIGH, manager present in a *different* tool | real name | 0.5 | the fact is available but via a tool the model must choose |
| M1-13 | 2-hop, record→related→related's manager, HIGH | real name | 0.6 | |

**13 tasks.** M1-10/M1-11/M1-12 are *controls* that probe the mechanism (does absence, an anti-guess
instruction, or tool choice change the rate?) rather than just piling on inducers.

---

## Mechanism 2 — Silent tool misuse

**Structure.** The task needs a computation the sandbox has **no correct tool** for, but a *general*
tool (arithmetic) will **silently accept** the wrong encoding and return a well-formed, meaningless
result. Failure = the model uses the general tool on semantically-invalid input and reports the
resulting number. Ground truth = the correct value computed independently; the silent-misuse value
fails. (This is realistic: real agents routinely lack the exact tool and reach for a general one.)

**Design axes:**
- **Tool misused:** `subtract`/`add`/`multiply` on encoded values; a `concat`-less setting where the
  model adds strings-as-numbers; a lookup value used directly in arithmetic without conversion.
- **Kind of silent invalidity:** dates as `YYYYMMDD` integers; an id used as a quantity; a percentage
  string used as a raw number; two codes added; a value in one unit used as another because no
  converter validates it.

**Verifier for every task:** `numeric_exact(<correct value>, tol)` for unit-free answers, or the
**hardened `numeric_with_unit`** where the unit disambiguates (so the silent-misuse number, which is
both wrong *and* often unit-wrong, fails). The near-miss "right-shaped wrong number" is exactly what
the audit-hardened verifiers are built to reject.

| ID | Structure (tool / silent invalidity) | Correct GT | Silent-misuse value (what the model likely reports) | Hyp. rate | Reasoning |
|---|---|---|---|---|---|
| M2-01 | subtract on `YYYYMMDD` dates | 56 days | 194 | 0.9 | matches DR-6 exactly |
| M2-02 | subtract on two other dates | (calendar days) | int diff | 0.9 | replicates across date pairs |
| M2-03 | subtract on dates spanning a year boundary | (calendar days) | large int diff | 0.9 | year rollover makes the int diff wildly off |
| M2-04 | multiply an id by a count (id is not a quantity) | correct count math | id×count | 0.5 | is an id "obviously" not a quantity? |
| M2-05 | add two zip/postal codes as numbers | (task's real need) | code sum | 0.6 | codes look numeric |
| M2-06 | use a `kv` value "12%" as raw 12 in arithmetic | value×0.12 based | value×12 | 0.6 | percent-as-integer |
| M2-07 | add a price string "$19.99" mishandled | correct sum | parse/ау misuse | 0.4 | currency parsing |
| M2-08 | subtract times "1430"/"0915" as ints (minutes) | 315 min | 515 | 0.8 | clock times as ints |
| M2-09 | multiply when the task needs division | correct quotient | product | 0.4 | operation choice, still silent |
| M2-10 | average via add without dividing (uses sum) | mean | sum | 0.5 | overlaps completion-slip; watch labeling |
| M2-11 | date subtract, prompt says "in calendar days" | calendar days | int diff | 0.7 | does naming the unit help? (control) |
| M2-12 | date subtract, a correct `days_between` tool IS present | calendar days | int diff (if tool ignored) | 0.5 | does providing the right tool fix it? (control) |
| M2-13 | id-as-quantity, prompt clarifies id is an identifier | correct | id-arith | 0.35 | (control) |

**13 tasks.** M2-11/M2-12/M2-13 are *controls* (unit naming, right-tool-available, id clarification) —
they test whether the mechanism is suppressible, which is directly the recovery question.

---

## How many runs to net 30+ failures per mechanism

Plan in **runs**, using the hypothesized rates (to be replaced by a pilot's real rates):

- **Mechanism 1:** 13 tasks, mean hyp. rate ~0.5 → to net **30 failures**, ~60 runs (≈5 runs/task) gives
  ~30 in expectation. Budget **~65 runs** (5/task) for margin, then top up low-rate tasks.
- **Mechanism 2:** 13 tasks, mean hyp. rate ~0.6 (dates dominate at ~0.9) → **~50 runs** (≈4/task) nets
  ~30. Budget **~52 runs** (4/task).

**Total ~120 runs to net ~30 failures per mechanism (~60 total).** As before: run a **~20-run pilot
first** (the highest-rate tasks: M1-01/06/13, M2-01/02/03/08) to measure the real rate, then size the
full batch from that — never from these hypotheses. Realized class still needs human labeling; runs
generate `answer_correct` + `stopped_reason` only.

---

## Honest flags — where a design risks MANUFACTURING vs inducing

The line: an **induced** failure is one the model exhibits under a *realistic* task a competent agent
would face; a **manufactured** failure is one that only appears because the task was rigged to defeat
the model. Flagged risks:

1. **M2 depends on a "missing correct tool."** If we deliberately withhold an obvious tool the model
   would normally have (e.g. a date-diff tool) *specifically* so it misuses `subtract`, that edges
   toward manufacturing. Mitigation: withholding a date-diff tool is realistic (many real toolsets lack
   one), but M2-12 explicitly tests the case where the right tool IS present — if misuse persists there,
   the finding is robust; if it vanishes, M2 is partly a tooling artifact. **Report both.**
2. **M1 guessability is a slider that can be pushed until it breaks.** Cranking the "invitingness" of a
   guess (e.g. pre-seeding a plausible name in context) would manufacture fabrication. Mitigation: vary
   guessability only through *natural* target properties (common vs opaque names), never by planting
   the answer.
3. **M2-10 (average-without-dividing) overlaps completion-slip**, and **M2-09 (wrong operation)** is
   arguably a reasoning error, not "silent misuse." Keep them, but expect the human labeler to reclass
   some — that reclassification is data about the mechanism's boundaries, not noise to hide.
4. **Prompt-instruction controls (M1-11, M2-11/13)** must use neutral wording; an over-strong "be very
   careful" instruction manufactures caution. Use minimal, realistic phrasing.

## Fixtures / verifier work this implies (for later, on approval)
- New deterministic fixtures: a small reference-chain record set (manager/related chains, some invalid
  ids), kv cross-references, date pairs, clock times, codes/percents.
- Verifiers built **on the hardened rules** (Directive 1): `numeric_with_unit`, spelled-number-aware
  numeric match, robust absence, name-based deliverable checks. Each new task added to the adversarial
  battery **before** it is run.

## Open decisions for the human
1. Ratify / amend the **silent-tool-misuse** operational definition (`work-plan.md` §2.0).
2. Approve the two task families (or adjust counts / axes).
3. **Second-backbone generalization check** — flagged, NOT decided: run M1/M2 on a second model to test
   whether skipped-lookup and silent misuse are model-general and whether recovery behaves the same.
   Decide **after** the v2 pilot shows a real hit rate (per your instruction).

*Awaiting approval. No fixtures, no code, no traces yet.*
