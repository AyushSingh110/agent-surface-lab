# PROJECT JOURNAL — `agent-surface-lab`

**The single narrative record: what was done, why, what blocked it, how each blocker was resolved, and what
the results actually are.**

*Maintained document — updated as work proceeds. Distinct from `LOGBOOK.md` (append-only, chronological, one
entry per action) and from `RESEARCH-NARRATIVE.md` (the scientific argument). This file is the operational
story: the path taken, including the wrong turns.*

Last updated: **2026-08-07**

---

## 0. What this project is

A research program testing one thesis:

> **LLM agents act on surface text and surface cues rather than the deeper property those cues are supposed
> to represent.**

The active study (`paper-recovery/`) asks: when an agent fails mid-run, does intervening actually recover it?
Recovery is measured **causally** — rewind to the failure step, apply one repair, replay forward, check a
deterministic ground truth against a **no-op control**. Never an LLM judge.

**Backbone:** local Ollama, pinned `qwen2.5:7b`. Hardware: Windows 11, 16 GB RAM, 4 GB VRAM (RTX 3050),
i7-12700H.

---

## 1. Where the project stood before this work

Completed earlier: harness (recorder, replay, interventions, metrics, verifiers), two induction task
families, a 1,692-replay recovery sweep, an N=10 firm-up, and a second-backbone attempt on Mistral. 82 tests.
A draft manuscript existed. Three headline findings had already been self-corrected during that work.

**The state at the start of this session:** a workshop-tier paper with two real findings, capped by a
single-model constraint and a synthetic sandbox, and carrying an unresolved flag in `paper/README.md` —
*"verify the three 2026-dated references."*

---

## 2. Phase 0 — Citation verification

### Why it came first
A fabricated or withdrawn citation in a published preprint is unrecoverable reputational damage. The project
had ~21 arXiv IDs, several dated 2026, and an explicit unresolved verification flag. Everything else was
gated behind this.

### What was done
Every arXiv ID in `paper/main.tex` and `docs/literature-review.md` was fetched from the live listing and
compared against how it was cited — title, authors, and the substantive claim attributed to it.

### Result — the headline is good
**All 21 IDs resolve. No fabricated citations.** The 2026-dated references that carried the most risk
(CausalFlow, Causal Agent Replay, FlowFixer) are real papers, and DoVer's ~49 % recovery figure — the number
that drove an earlier framing pivot — is confirmed verbatim in its abstract. The scoop analysis underpinning
the project's positioning was built on real work.

### Blockers / problems found
| Problem | Resolution |
|---|---|
| **4 wrong titles** in the bibliography — `agentracer` was a paraphrase, not the real title; `car`'s entire subtitle was wrong; `causalflow` contained a word ("Minimal") not in the title; `flowfixer` used the system name as the title | All corrected; author lists added to 7 entries that had none |
| 🔴 **GraphTracer (2510.10581) was WITHDRAWN** by its authors on 2025-12-22 for "a fundamental error in the methodology" — and was cited as valid supporting evidence in 3 internal docs, with `paper-outline.md` slating it for Related Work | Flagged as withdrawn in all 4 locations rather than silently deleted. The "attribution is saturated" argument does not depend on it — five other papers carry it independently and all verify clean |

### Incidental finding that shaped Phase 1
Causal Agent Replay's abstract advertises *"confidence intervals for all reported effects."* A directly
neighbouring paper already reported uncertainty while ours reported bare point estimates — a visible
comparative gap.

**Artifact:** `docs/citation-verification.md`, plus a standing rule that new citations are verified before
entering any doc.

---

## 3. Phase 1 — Confidence intervals (zero new compute)

### The problem
Every published rate was a bare point estimate over as few as **6 traces**, with no uncertainty reported
anywhere in the paper.

### The insight that made it free
The firm-up checkpoint (`recovery_firm/cells.jsonl`) stores the **full per-replay boolean list** for every
cell. That is exactly what a bootstrap needs — so the intervals came from data already on disk. **No model
calls.**

### Method decision (and why it matters)
A **two-level** bootstrap: resample *traces* with replacement, then resample each drawn trace's 10 replays.
With m=6..23 traces per cell, **between-trace variation dominates replay noise**; a replay-only bootstrap
would treat the particular six depth-3 traces as the population and produce intervals far too narrow.

Contrasts are **paired** — one set of drawn trace indices evaluated under both arms — because every arm ran
on the same traces. This is what allows an interval on the *contrast itself* rather than on two separate rates.

**Degenerate cells:** an all-zero cell bootstraps to `[0,0]`, which asserts a certainty we do not have. Those
get a **cluster-level rule-of-three bound** (3/m over traces, not 3/mN over replays, since replays of one
trace are not independent trials).

### Results
**The headline claim survived and became statistically supported.** Paired
`lookup_permitting − declarative_neutral`:

| depth | difference | excludes zero |
|---|---|---|
| 1 (m=21) | **+0.84 [+0.74, +0.92]** | ✅ |
| 2 (m=23) | **+0.57 [+0.47, +0.66]** | ✅ |
| 3 (m=6) | **+0.40 [+0.23, +0.55]** | ✅ |

**A claim was found to be overstated.** "Tool-false-validation resists *every* text-level repair" did not
survive: `reflect_and_retry` clears zero on both surface forms (+0.05 [+0.01, +0.12] date; +0.14
[+0.04, +0.25] clock). Verified against raw cells before changing anything — on clock forms `no_op` is a hard
**0/110** across all 11 traces while `reflect` recovers **15/110**, concentrated in 5 traces. Real, small, and
against a clean zero floor. Restated as *"resists text repair almost completely; only reflect has a
detectable effect, leaving ≥86 % unrecovered."*

**Three smaller things the intervals exposed:**
- `no_op` at depth 1 (0.07 [0.00, 0.16]) is driven mostly by **one** self-recovering trace — not a stable rate.
- `no_op` at depth 3 cannot be called ≈0: all six traces all-zero → honest bound **≤0.50**.
- The mood refutation holds at depths 1–2 but **not** depth 3, where the two arms coincide exactly.

**Artifacts:** `harness/bootstrap.py` (pure stdlib, so numpy stayed deferred), `tests/test_bootstrap.py`
(26 tests), `paper-recovery/analysis_ci.py`. Tests 82 → 108.

---

## 4. Phase 2 — The repair-surface factorial

### The problem this existed to solve
The headline rested on **one contrast** whose two sentences differed in **four** ways at once: permission,
tool-mention, length, and second-clause presence. "Action-licensing" was **not identified**. A reviewer could
have dismissed it in one sentence — *"you primed it with the word 'tools'"* — and been right.

### Design
All five arms share the identical base `Report {core}`; only the trailing clause varies. Licensing is crossed
against tool-mention, with a **length-matched placebo** granting nothing and naming nothing.

A design improvement found mid-build: `req_imperative_plain` was already `"Report {core}."` — the same base —
so two of the five cells already existed at N=10 and were **reused rather than re-run**, keeping the
comparison on identical replays. Consistency check passed: both reproduce exactly when pooled across depth.

**Cost:** 150 cells / 1,500 replays.

### Results — three separable channels

| arm | licenses | tools | recovery |
|---|---|---|---|
| `license_no_tool` | ✓ | ✗ | **0.94 [0.89, 0.98]** |
| `lookup_permitting` (original winner) | ✓ | ✓ | 0.84 [0.77, 0.90] |
| `placebo` | ✗ | ✗ | **0.79 [0.72, 0.86]** |
| `tool_no_license` | ✗ | ✓ | **0.57 [0.46, 0.68]** |
| *(no clause)* | — | — | 0.49 [0.39, 0.60] |

1. **Salience is the largest channel: +0.30 [+0.18, +0.42].** Appending *"this is an important requirement"* —
   no information, no permission, no capability reference — lifts recovery from 0.49 to 0.79. Most of what
   looked like designed repair is **the presence of a second sentence.**
2. **Licensing is real and survives on top: +0.15 [+0.09, +0.21].** Content matters — at roughly half the size.
3. **Naming tools actively HARMS: −0.22 [−0.33, −0.12].** *"Tools were available for this task"* is worse than
   saying something meaningless.

### The mechanism check (why finding 3 is trustworthy)
A negative effect is the most attackable claim, so the divergent traces were replayed with full output
capture. Under the placebo the model issues the missing `get_record` and answers correctly (3/3). Under
tool-mention it makes **no tool call at all** (2/3) and chains from context — *"the manager of #211 is
Node-77, and the manager of Node-77 is Unit-Alpha"* — fabricating the link it was meant to fetch.

The tools are equally available in both conditions. The only difference is a **past-tense, descriptive**
sentence, which reads as though the tool phase is over. **The repair re-induces the exact failure it was
meant to fix.**

### The consequence for the project's own headline
`lookup_permitting − placebo` = **+0.04 [−0.02, +0.10] — contains zero.** The original hero arm is
statistically indistinguishable from appending a contentless clause, because its licensing benefit is very
nearly cancelled by its own tool-mention cost. **The 1.00-vs-0.16 observation was real; the explanation was
wrong.**

**Artifacts:** `paper-recovery/run_factorial.py`, `analysis_factorial.py`, new manuscript §6, and a blog post
(`blog/the-placebo-that-fixed-my-agent.md`).

---

## 5. Phase 3 — Model screening

### Blocker 1: the disk was full 🔴
**Symptom:** 476 GB drive at **100 %**, 1.1 GB free. No model could be downloaded.
**Diagnosis:** not caused by this project — all of `data/` is **3.4 MB**. Ollama held ~34 GB across 9 models.
**Resolution:** removed unused models after verifying against the repo that none were referenced.

### Blocker 2: the primary backbone was accidentally deleted 🔴🔴
**What happened:** a multi-argument `ollama rm` removed the **wrong models**. Intended llama2/llama3/phi3/
gemma3; actually removed **`qwen2.5:7b`** (the primary backbone), phi3, and gemma3, while llama3 survived. The
command errored partway ("llama2 not found") and argument handling went wrong from there.

**Impact assessment (done immediately):** **no research data lost** — `traces.jsonl`, `labels.json`, and both
`cells.jsonl` files verified intact and never at risk.

**Why it was not a reproducibility disaster:** Ollama models are **content-addressed**. `qwen2.5:7b` was
re-pulled and its digest verified as **`845dbda0ea48` — an exact match** to the digest that produced every
number in the paper. Had it differed, every recovery result would have needed re-running.

**Secondary error:** the first re-pull reported exit code 0 but had actually failed
("timed out waiting for server to start") — a `| sed | tail` pipeline masked the real exit status. Caught by
verifying the model list instead of trusting the exit code.

**Root cause of both:** acting on an *assumed* result rather than a *verified* one.
**Process changes adopted:** single-target deletes with explicit before/after listing; check real exit codes;
verify digests after any model change.

### Blocker 3: the Ollama server stopped serving
Log showed `existing instance found, exiting` — the tray process existed but the API was dead. Resolved by
restarting via `ollama serve`. This also triggered blob garbage collection, reclaiming ~12 GB that the botched
delete had orphaned (1.1 GB → 20 GB free).

### Blocker 4: the screening instrument did not exist 🔴
**Found while starting Phase 3:** the original smoke test was a **throwaway scratchpad script, never
committed** (LOGBOOK 2026-07-21: *"scripts in scratchpad (throwaway, not committed)"*). So the recorded
`llama3.1 0/6`, `mistral 3/6`, `qwen 6/6` — **Table 5, and the entire evidence base for the C6b
tool-capability contribution — could not be reproduced by anyone.**

**Resolution:** rebuilt as committed code — `paper-recovery/screen_models.py` (6 two-step chaining tasks,
temp 0 / seed 7, `PASS_THRESHOLD = 6` **pre-committed in source** so the bar cannot drift toward whatever a
candidate scores) plus `tests/test_screen.py` (16 tests). Tests 108 → 124.

Two judging decisions that are scientific, not cosmetic:
- **A correct answer without threading is NOT clean.** A model that reasons in text cannot be repaired by a
  tool-based intervention — exactly what the screen predicts — so admitting it would inflate a
  generalization claim.
- **A task must not leak its own intermediate value.** A test enforces this; otherwise "threading" is
  unfalsifiable, since the model could echo the number without using the tool's return.

### Blocker 5: calibration FAILED — then explained
Because the new instrument uses the real harness runner while the original used a bespoke loop, agreement
was not guaranteed. Calibration against the three recorded models:

| model | recorded | measured | |
|---|---|---|---|
| `qwen2.5:7b` | 6/6 | 6/6 | ✅ agrees |
| `mistral:7b` | 3/6 | **0/6** | ❌ disagrees |
| `llama3.1:8b` | 0/6 | 0/6 | ✅ agrees |

**Diagnosis:** Mistral makes **one tool call, then completes step two in text** and reports the correct
answer — 5/6 correct, 0/6 chained. The instruments measure different things: the old one credited "used a
tool and got it right"; the new one requires threading a tool result into a second call, which is the
capability every recovery arm depends on.

**This CONFIRMS the earlier Step-2 conclusion rather than contradicting it.** The Mistral pilot had
categorized 16 traces as *"no-tool-call (reasoned in text)"* and concluded recovery was untestable for exactly
this reason. **The recorded 3/6 understated the problem.**

**Honest caveat:** the original tasks were lost with the scratchpad, so the six tasks are a reconstruction and
exact reproduction was never possible. Notably both **extremes** reproduce exactly while the **borderline**
model does not — extreme scores are robust to instrument details, mid-range ones are not, which is itself a
reason not to quote 3/6 as a stable property.

### Screening results — 6 models, 2 admitted

| model | clean chains | verdict | correct but never chained |
|---|---|---|---|
| **`qwen2.5:7b`** | **6/6** | ✅ ADMITTED | — |
| **`qwen3:8b`** | **6/6** | ✅ ADMITTED | 0 |
| `granite3.3:8b` | 1/6 | rejected | 5/6 |
| `mistral:7b` | 0/6 | rejected | 5/6 |
| `llama3.2:latest` | 0/6 | rejected | 6/6 |
| `llama3.1:8b` | 0/6 | rejected | — |

**The finding, which sharpens C6b considerably:** four of six models are **outcome-competent but
chain-incompetent** — they answer correctly (granite 5/6, mistral 5/6, llama3.2 6/6) while threading a tool
result zero or one time. They are not "bad at tools" in the way an outcome benchmark would report. **Chaining
is the capability every text-level repair depends on, and outcome-based tool benchmarks do not measure it.**
`granite3.3:8b` — explicitly marketed for function calling — chained exactly once in six attempts.

**The threshold was not lowered** to admit granite's near-miss. That is precisely the drift pre-commitment
prevents.

### Blocker 6: only same-family replication is possible
Both admitted models are Qwen. After six models screened, **no different-family model at this scale is
eligible**, so the replication tests **generation**-generality, not family-generality — weaker, and the
write-up must say so.

**A confound recorded deliberately:** qwen3 runs with reasoning ("thinking") mode on by default; qwen2.5 has
no such phase. Any difference conflates generation with the presence of reasoning. This cuts one way usefully:
**if the findings replicate despite it, the evidence is stronger** than a like-for-like comparison. If they
diverge, the divergence is not attributable to generation alone.

### Blocker 7: the replication pilot is slow (current)
qwen3's reasoning mode costs ~3.7 min/run on 4 GB VRAM → **~5.7 hours** for 93 runs. The pilot also survived a
Claude-process exit as an orphaned process and continued running; a stall-detecting monitor was re-armed
rather than restarting the run and losing progress.

**Status: IN PROGRESS.**

---

## 6. Phase 4 — Provenance study (specified, not started)

Spec at `docs/phase4-provenance-killtest.md`. Kill test first, per CLAUDE.md §6.

**Hypothesis (H-PROV):** *an agent assigns epistemic status by the CHANNEL a fact arrived on, not by the
fact's content.*

**Origin:** already half-observed in LOGBOOK 2026-07-25 — *"the misuse fires when the date ARRIVES AS A TOOL
RESULT, not when stated in the prompt"* — 12/12 clean via `kv_lookup` vs ~0 when prompt-stated. **But that
observation is confounded**: those tasks varied chain depth *and* channel together. The kill test must hold
depth fixed and vary only channel, or it repeats the mistake that forced C2 into a factorial.

**Design:** 8 facts × 2 channels (prompt-stated vs tool-returned) × N=10 = **160 runs**. Primary measure:
does the agent issue a corroborating tool call before using the fact? Secondary: under contradiction, which
channel wins? Both deterministic booleans — immune to the string-matching failures that bit v1 three times.

**Pre-committed kill criteria:** gap < 0.15 with CI containing zero → **hypothesis dead**, report the null,
do not build the full study.

**Why it is worth doing:** the prompt-injection literature measures *attacks succeeding*; it has never
established the **base-rate trust ordering over channels** that makes them work.

---

## 7. Running list of blockers and resolutions

| # | Blocker | Severity | Resolution | Status |
|---|---|---|---|---|
| 1 | Unverified citations, several 2026-dated | High | All 21 verified live; 4 titles fixed | ✅ Resolved |
| 2 | A cited paper was **withdrawn** | High | Flagged in 4 locations; argument re-based on 5 clean sources | ✅ Resolved |
| 3 | No uncertainty on any published number | High | Two-level paired bootstrap, zero new compute | ✅ Resolved |
| 4 | Headline claim **not identified** (4 confounds) | High | 1,500-replay factorial with length-matched placebo | ✅ Resolved |
| 5 | A claim was **overstated** ("resists every repair") | Medium | Restated with intervals; verified against raw cells | ✅ Resolved |
| 6 | Disk 100 % full | Blocking | Removed unreferenced models; blob GC via server restart | ✅ Resolved |
| 7 | **Primary backbone deleted by mistake** | Critical | Re-pulled; digest verified identical; no data lost | ✅ Resolved |
| 8 | Failed pull masked by pipeline exit code | Medium | Verify state, not exit codes | ✅ Resolved |
| 9 | Ollama server stopped serving | Blocking | `ollama serve` restart (also reclaimed 12 GB) | ✅ Resolved |
| 10 | **Screening instrument never committed** → Table 5 unreproducible | High | Rebuilt as tested, pre-committed code | ✅ Resolved |
| 11 | Calibration disagreement on Mistral | Medium | Diagnosed; new instrument is correct; Table 5 correction pending sign-off | ⚠️ Needs decision |
| 12 | No different-family model is eligible | Structural | Accepted + documented; same-family replication instead | ⚠️ Documented limit |
| 13 | qwen3 pilot ~5.7 h (reasoning mode) | Low | Monitored; allowed to run | 🔄 In progress |

---

## 8. Current state

**Tests:** 124 passing. **Compute this session:** ~1,500 replays (factorial) + ~18 (spot-check) + ~54
(screening). Phases 0 and 1 cost zero model calls.

**Decisions awaiting the human (science, not engineering):**
1. **Table 5 correction** — Mistral `3/6` → `0/6 clean chains (5/6 correct without chaining)`.
2. **Phase 4 approval** — H-PROV, the 0.15 kill threshold, verification-rate as primary measure.

**Honest summary of the session's effect on the paper:** one headline was decomposed and partly overturned by
a control the study had never run; one claim was softened; one contribution (C6b) was substantially
strengthened and made reproducible for the first time; and the citation base was verified clean. Three
separate corrections were caught by checks chosen internally rather than by a reviewer.
