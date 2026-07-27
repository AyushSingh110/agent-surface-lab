# LOGBOOK — `agent-surface-lab`

The running record of what has been executed and why. Append-only; never overwrite past entries.

---

## 2026-07-21 — Config change to Ollama-only; work plan approved; kill-test A design decisions (partial)
**What:**
- Updated `CLAUDE.md` §4 (reproducibility), §6 (backbone line), §7 (environment) from a Groq+Ollama pair to a
  single local Ollama backbone. Diff shown to the human; not committed (file is still untracked).
- Wrote `docs/work-plan.md` (Phase 1). Approved by the human at GATE 1.
- Recorded the human's design decisions for the Recovery kill test.
**Why:** Configuration is now Ollama-only (no hosted APIs). Work plan governs sequencing of the three studies
(paper-recovery = Ideas A+B first, paper-toolseo = Idea C second) and specifies each study's kill test with
positive/null criteria, per CLAUDE.md §6.
**Config:** No experiment run yet. Backbone: single local Ollama model (specific model TBD in Phase 3, pending the
human's RAM/GPU).
**Result / decisions on record:**
- DECIDED — Kill-test A interventions: reflect-and-retry, rollback-2, requirement-injection.
- DECIDED — Detection at step *k*: use the oracle-labeled failure step for the kill test.
- PENDING — Trace provenance (ARIA reuse / fresh generation / hand-curated): the human's reply still contained the
  bracketed template, so this is NOT decided. Blocks kill test A.
- PENDING — Failure-class labeling protocol: still bracketed. Blocks kill test A.
- PENDING — Ground-truth definition (exact-match / file-written / fact-correctness): still bracketed. Blocks kill
  test A.
**Next:** GATE 2 — literature scan (`docs/literature-review.md`). The three PENDING decisions must be resolved
before Phase 4 (kill test A) can run; flagged to the human.

---

## 2026-07-21 — Literature scan (GATE 2); two novelty risks surfaced
**What:** Wrote `docs/literature-review.md` — 20 real, located sources across the recovery and toolseo clusters,
with per-paper summaries, a gap-analysis table, honest novelty verdicts, and framing notes. Read AgenTracer,
FlowFixer, BiasBusters, and Agent-Facing Information Design in full; the rest at abstract level (marked in-doc).
**Why:** Gate 2 requires grounding our framing and confirming novelty before any build.
**Config:** N/A (desk research). Web access available and used.
**Result — the two findings that matter:**
- **toolseo (Idea C): original RQ1 is largely SCOOPED.** *Agent-Facing Information Design in LLM Tool Registries*
  (arXiv:2605.23916, ~17,700 experiments, capability held constant) and *BiasBusters* (arXiv:2510.00307, ICLR
  2026) already show description text moves selection and that prompt-warning defenses fail. 2605.23916 explicitly
  leaves open whether agents *learn to discount* manipulative descriptions after failure — i.e. our RQ3. Verdict:
  study needs a PIVOT toward RQ3 (persistence-after-failure) + execution-outcome reputation defense, with the
  attack as reproduction/setup not headline. This is a science decision → flagged to the human, not decided.
- **recovery (A+B): gap still REAL but shrinking.** No paper does a counterfactual-replay recovery matrix with an
  iatrogenic rate. FlowFixer (arXiv:2607.02882) is the nearest repair paper but uses symbolic inference, reports
  only aggregate repair rate (~71.3%), and measures no iatrogenic harm or Pareto. **Open risk: "DoVer"** (cited by
  FlowFixer as intervention-and-replay causal-effect estimation) is UNREAD and could partially scoop our method —
  must be pulled and read before finalizing the recovery framing.
- **ARIA predecessor project: not located publicly.** Could not confirm a public ARIA repo/paper; left unverified
  rather than guessed.
**Next:** Await GATE 2 approval. Before Phase 4: (1) read DoVer; (2) human's call on the toolseo pivot; (3) human
resolves the three PENDING kill-test-A decisions (trace provenance, labeling protocol, ground-truth definition).

---

## 2026-07-21 — ARIA inspection + three blocking kill-test-A decisions resolved
**What:** Inspected the human's ARIA project (`c:/Users/ASUS/Desktop/ARIA`) to ground the trace-provenance
decision, then recorded the human's picks on items 1, 2, 4.
**Why:** These three decisions block Phase 4 (Recovery kill test); they set where traces come from, how failure
class is labeled, and what "success" means.
**Findings from ARIA (facts, not assumptions):**
- Per-step trace granularity exists and is replay-grade: each result's `trace` is a list of
  `{turn, tool_name, tool_args, tool_result, llm_output, latency_ms, token_count}`.
- Ground truth exists as `answer_correct: bool` vs a stored `expected_answer`.
- Taxonomy is identical to ours: `prompt_drift, tool_misuse, context_overflow, hallucination_loop,
  goal_misalignment` (+ `none`, `gap`, `multi`, `unclear`), with a full decision-tree labeling guide at
  `ARIA/docs/labeling-guide.md`. But only ARIA's own `aria_label` (model prediction) is populated locally;
  `human_label` is empty, and only ~10 result files are on disk (bulk gitignored). All ARIA traces were generated
  on Groq `llama-3.1-8b-instant` — a backbone mismatch against the new Ollama-only config, which is why reuse was
  rejected.
**Decisions (human):**
- Item 1 — Provenance: **Option C, generate fresh traces on the pinned Ollama model.** Skip reuse (Option B)
  entirely to avoid the Groq→Ollama replay confound; runner+recorder is on the critical path anyway.
- Item 2 — Labeling: **adopt ARIA's `labeling-guide.md` verbatim, incl. exact class names** (matrix rows renamed
  to `prompt_drift/tool_misuse/context_overflow/hallucination_loop/goal_misalignment`). Single labeler + written
  decision tree at kill-test scale; two-annotator + Cohen's κ for the full study. **Rubric addition:** record BOTH
  failure class AND oracle failure step *k* per trace.
- Item 4 — Ground truth: **per-task-type deterministic verifier → single `answer_correct` boolean.** Numeric →
  normalized exact-match; open QA → fact-match/F1; file tasks → file-existence+content; transactions →
  environment-state. **Hard constraint: never an LLM judge.**
- Still DECIDED earlier: item 3 (interventions), item 5 (oracle *k*).
**Config:** No experiment run. Backbone still TBD (Phase 3 — pending human's RAM/GPU).
**Next:** Phase 3 environment setup. Ask the human's RAM/GPU, recommend one default Ollama model for agentic
tool-use + a lighter fallback, and give exact Windows install/pull/serve/verify commands. Do NOT write
runner/recorder code until the human confirms the model responds. ToolSEO/Gate 2 pivot deferred at human's request
(does not block Recovery).

---

## 2026-07-21 — Phase 3 environment setup (Ollama-only); GATE 3 pending
**What:** Wrote `docs/setup.md` (LIST A manual commands / LIST B my commands, tailored to Windows cmd), `.gitignore`,
`.env.example`, and `pyproject.toml` with flagged, minimal dependencies. No code written yet.
**Why:** Phase 3 prepares the single local backbone before any harness code (Option C needs the model pinned first).
**Config / hardware:** Human's machine — Windows 11, 16 GB RAM, 4 GB VRAM, i7-12700H, ~477 GB free. Priority:
reliable tool-calling.
**Result / decisions:**
- **Model pin recommendation:** default `llama3.1:8b` (native tool-calling; same family as ARIA's Groq
  llama-3.1-8b-instant → continuity), lighter fallback `llama3.2:3b`. Qwen2.5:7b noted as an alternative the human
  can choose instead (their call). Final pin confirmed once the human runs LIST A and picks.
- **Dependencies flagged (pyproject):** runtime = `ollama`, `pyyaml`, `python-dotenv`; dev = `pytest`. Deferred and
  NOT installed: numpy/scikit-learn/xgboost/matplotlib (Idea B), dspy-ai (toolseo) — each to be approved before adding.
- `.gitignore` excludes `.env`, `.venv/`, `data/`, `*.jsonl`, model caches, `__pycache__` (CLAUDE.md 4/5).
**Next:** GATE 3 — human reviews setup.md + .gitignore + deps, then runs LIST A and confirms A4 (model responds).
Only after that: install deps (B1), tool-calling smoke test (B3), then scaffold + minimal kill-test harness (Phase 4,
gated). No runner/recorder code until confirmation.

---

## 2026-07-21 — Env switch to conda `surface`; deps installed; verified install target
**What:** Human switched from venv to a conda env. Updated `docs/setup.md` (LIST A now uses
`conda create -n surface python=3.11`/`conda activate surface`; venv steps removed) and `.gitignore` (dropped the
`.venv/`/`venv/` block — conda envs live outside the repo). Verified the install target, then installed the four
approved deps.
**Why:** All dependencies must land in `surface`, never base/venv. My command-tool shell is a separate session
from the human's activated terminal, so installs target the env explicitly via `conda run -n surface`.
**Verified environment (record of where deps land):**
- name: `surface`
- prefix: `C:\Users\ASUS\anaconda3\envs\surface`
- python: `3.11.0`
- (confirmed via `conda run -n surface python -c "import sys; print(sys.prefix, sys.version)"` — NOT base, NOT a venv)
**Config:** Ollama up; `llama3.1:8b` confirmed responding by human (A4 = OK). Deps approved by human: `ollama`,
`pyyaml`, `python-dotenv`, `pytest`. Deferred: numpy/sklearn/xgboost/matplotlib, dspy-ai.
**Result — install (B1/B2):** Installed into `surface` via `conda run -n surface pip install -e ".[dev]"`:
`ollama==0.6.2`, `pyyaml==6.0.3`, `python-dotenv==1.2.2`, `pytest==8.4.2` (+ transitive httpx/pydantic/anyio).
Confirmed all import from the surface prefix (`sys.prefix` ends in `envs\surface`; not base/venv). Locked with
`pip freeze --exclude-editable > requirements.txt`. Note: surface pre-contained jupyter/ipykernel packages (not
ours); deferred deps (numpy/sklearn/xgboost/matplotlib/dspy) confirmed ABSENT.

**Result — tool-calling smoke test (B3), reported honestly:** Ran two variants of a minimal 2-tool (add/multiply),
2-step ReAct loop over 6 arithmetic tasks against `llama3.1:8b` (temp 0, seed 7). Scripts in scratchpad (throwaway,
not committed).
- v1 (bare numeric tool-result feedback): valid-toolcall runs **1/6**; 4/6 had a malformed 2nd call; 1/6 returned
  empty output.
- v2 (tool-name attached to result + explicit "never pass 'result'" instruction + error-and-retry): clean
  multi-step runs **0/6**, but correct final answer **6/6** after a forced re-call.
- **Consistent failure mode:** on the SECOND step the model passes the literal string `"result"` as a tool
  argument (`{'a':'result','b':N}`) instead of threading the first tool's returned number — 100% of the time in v2.
  It recovers only when the scaffold returns an error prompting a re-call. First-step tool calls are reliable.
- **Interpretation:** `llama3.1:8b` on Ollama is reliable at single tool calls but **unreliable at multi-step tool
  chaining** (argument-threading), in a highly consistent, almost deterministic way. This is not a fluke of the v1
  harness — improving feedback did not fix the first-attempt malformation.
- **Why it matters for the build (flagged to human, NOT decided):** (1) it will skew induced failures toward one
  `tool_misuse`-like artifact unless tasks are designed around it; (2) the scaffold's error-feedback strongly
  shapes recovery, which could inflate the apparent efficacy of the "tool re-call" intervention (a validity
  concern for H2); (3) tension with the ARIA-continuity rationale for pinning llama3.1. Options surfaced: design
  kill-test tasks to be mostly single-tool-call; OR compare `qwen2.5:7b` (often stronger at chaining) before
  finalizing the pin; OR embrace the artifact as a reliable tool_misuse generator with deliberate task diversity.
**Next:** STOP at GATE 4. Await human's steer on the backbone/scaffold implication before building the
runner/recorder harness. No harness code written.

---

## 2026-07-21 — Backbone comparison: qwen2.5:7b vs llama3.1:8b on multi-step tool use
**What:** At the human's request, pulled `qwen2.5:7b` and ran the identical B3 smoke test (both v1 and v2 variants,
same 6 two-step tasks, temp 0, seed 7).
**Why:** llama3.1:8b's 0/6 clean multi-step rate threatened trace quality and H2 validity; needed head-to-head data
before pinning the backbone (work-plan §8 item 8).
**Result (clean, honest):**
- `qwen2.5:7b`: **v1 6/6 clean, v2 6/6 clean**, 6/6 correct finals. It correctly threads the first tool's returned
  number into the second call every time — zero malformations, in both feedback regimes.
- `llama3.1:8b` (prior entry): v1 1/6, v2 0/6 clean; 100% malformed 2nd-step arg-threading.
- **Verdict: qwen2.5:7b is dramatically more reliable at multi-step tool chaining on this hardware.**
**Trade-off for the pin (human's decision):** qwen2.5:7b = clean, controllable substrate (induced failures are the
ones we design, not an uncontrolled artifact) but breaks the ARIA-model-family continuity narrative. Since provenance
is Option C (fresh traces), continuity is only a framing point, not a data dependency — so the cost of switching is
low. llama3.1:8b = ARIA continuity but a confounded substrate.
**Config:** both models present in Ollama now (`llama3.1:8b`, `qwen2.5:7b`). `.env` still points at llama3.1:8b.
**Next:** GATE 4 — human picks the backbone to pin (update `.env` / `.env.example` + work-plan §8 item 8 accordingly).
No harness code until the pin is set.

**Decision (2026-07-21):** Human pinned **`qwen2.5:7b`**. Updated `.env.example` (OLLAMA_MODEL=qwen2.5:7b) and
work-plan §8 item 8 (DECIDED). No local `.env` exists yet — the config loader will default to qwen2.5:7b, and the
human can `copy .env.example .env` if they want to override. Backbone is now fully pinned; all §8 items that block
Phase 4 are resolved. Ready to scaffold the minimal kill-test harness on Gate 4 approval.

---

## 2026-07-21 — DoVer deep-read (scoop check before freezing replay design)
**What:** Read DoVer (arXiv:2512.06749, Dec 2025) and, while locating it, two direct neighbours — CausalFlow
(2605.25338) and Causal Agent Replay (2606.08275). Wrote a full memo appended to `docs/literature-review.md`
(Addendum). This resolves the `[LEAD]` flag on DoVer.
**Why:** Human required a scoop/reshape check on the recovery method BEFORE the recorder/replay schema is frozen.
**Result — honest findings:**
- **DoVer overlaps our core.** It applies interventions at a failure step and validates by counterfactual replay
  (milestone/utility progress, not an LLM judge), and explicitly reframes from attribution toward RECOVERY/repair —
  recovering ~49% of failed trials (GSMPlus/AG2; also GAIA, AssistantBench on Magentic-One). So our "detection is
  not repair / verify recovery by replay" STANCE and RQ1 are partially SCOOPED (also by CausalFlow + CAR). Not softened.
- **What DoVer/cluster do NOT do (our remaining contribution):** no IATROGENIC rate; no principled intervention ×
  failure-CLASS recovery matrix (DoVer's class breakdown is loose/uncertain in my read); no LATENESS-decay curve; no
  bridge to early PREDICTION (Idea B). Plus we have tighter causal hygiene: oracle-k, deterministic ground truth,
  single-agent.
- **Design lessons acted on:** (1) recorder must let us reconstruct the FULL message/context state up to step k, not
  just tool calls — add a per-step context field or a tested reconstruct(); (2) must choose+log a DETERMINISM policy
  for replay (fix seed/temp=0 single-sample vs N≥3 sampled replays reporting a recovery distribution) — this is the
  stochastic-replay confound DoVer ignores; I lean N≥3 but it's the human's statistical-plan call (§8 item 10);
  (3) keep ground truth deterministic and detection/repair decoupled (both already decided) as edges over DoVer.
- **Verdict:** PROCEED WITH SHARPENED FRAMING (not a pivot). New headline centers on the class-conditional,
  IATROGENIC-aware recovery accounting + lateness + the Idea-B prediction bridge, built ON TOP of DoVer/CausalFlow/CAR
  as cited foundation. Old "you should intervene, not just detect" headline is retired (DoVer said it).
**Config:** desk research only; no code.
**Next:** STOP and await human's call. New open item for the human before/with Phase 4: §8 item 10 (determinism/
replay-sampling policy) now has concrete options to choose from. No harness code until Phase 4 is approved.

---

## 2026-07-21 — Phase 4 approved: reframing locked + kill-test harness build
**What:** Human green-lit Phase 4 and locked two decisions. Recorded the reframing and updated `docs/work-plan.md`
(§2 spine + §2.1 central claim; §8 item 10 DECIDED), then built the minimal kill-test harness.
**Why:** DoVer/CausalFlow/CAR occupy the "intervene-and-verify-by-replay" stance, so the contribution sharpens to
the one thing none of them measure — the iatrogenic rate.
**Decisions (human):**
- **FRAMING:** retire "detection is not repair / you should intervene." New spine: *"not all repair helps — which
  intervention recovers which failure class, and where standard self-correction actively harms."* **Iatrogenic rate
  is the central contribution.** The **no-op control arm** (re-run from k unchanged) is the differentiator vs DoVer
  and is first-class, never dropped for compute.
- **DETERMINISM (§8 item 10):** Option (b) — N replays per (intervention, trace), report a recovery-rate
  DISTRIBUTION. N config-switchable (default 3; N=1 for fast iteration); N=3 is a floor (metrics can raise N per
  cell near a decision boundary). Log seed, temperature, model tag on every replay.
- **DESIGN LESSON 1 (approved):** recorder captures enough to reconstruct the FULL running message/context state up
  to step k; `reconstruct()` is tested to reproduce the exact prompt the model saw.
**Config:** backbone qwen2.5:7b (pinned); seed default 20260721; N default 3.
**Result — harness built, tests green.** Scaffolded `harness/`, `paper-recovery/`, `tests/`. Modules:
`config` (seeded, .env+YAML, per-replay seed offset), `trace` (StepRecord/TraceRecord + `messages_appended_by` as
the single context-growth definition), `recorder` (one-trace-per-JSONL-line + build/append/load), `backend`
(ChatBackend protocol; OllamaBackend injected + FakeBackend for tests), `tools` (deterministic sandbox +
registry), `runner` (resumable ReAct loop; sole StepRecord construction site), `replay` (`reconstruct` +
`replay_cell` returning an N-length success distribution; InterventionOutcome/Verifier types), `interventions`
(no_op control + reflect_and_retry + rollback_2 + requirement_injection), `metrics` (macro recovery, paired
iatrogenic rate vs no_op, net_improvement, `is_near_boundary` for per-cell N-raising, recovery_matrix),
`verifiers` (deterministic only — numeric_exact/fact_match/file_written). **`pytest` = 30 passed** in the `surface`
env; `compileall` + import check clean.
- Design-lesson-1 satisfied: `tests/test_replay.py` proves `reconstruct(trace,k)` equals both the recorded
  `context_snapshot` AND the FakeBackend's independently-captured context, for every k.
- §8-item-10 satisfied: `replay_cell` returns a length-N distribution; config seed is offset per replay; N is
  config-switchable; `metrics.is_near_boundary` flags cells to re-sample.
- Iatrogenic centrality satisfied: `no_op` is the first arm; `metrics.iatrogenic_rate` is a paired,
  strict-worse-than-no_op comparison.
- No fabricated data: ground-truth/label fields default None; README carries NO results (CLAUDE.md §3/§5).
**Config:** tests use FakeBackend (no live model needed); kill-test run config at
`paper-recovery/configs/kill_test.yaml` (qwen2.5:7b, temp 0.7, N=3).
**Next:** GATE 4 — human runs the test commands. Real kill test still needs the human to (a) generate ~30 traces
on qwen2.5:7b, (b) label failure_class + oracle k, (c) wire the deterministic verifier per task. README/aggregate
results only after a real reproduced result.

---

## 2026-07-21 — Kill-test task suite spec (proposal, no code)
**What:** Wrote `docs/kill-test-tasks.md` — a written spec (no code) proposing 36 candidate tasks (6 per ARIA
class), the deterministic tool sandbox they need, each task's deterministic verifier + exact ground truth, an
over-provisioning plan, and honest weak-spot flags.
**Why:** The human wanted the task suite designed before the driver, since the tasks ARE the experiment (they set
which failure classes can appear; each verifier is a recovery-rate denominator).
**Result / key content:**
- Per-class induction mechanisms: drift = multi-goal + tool-result "related:#NN" hooks; tool_misuse = brittle tools
  (div/0, unsupported units, missing files/keys); context_overflow = long state-dependent chains; hallucination_loop
  = facts absent from all tools (separates honest models from confabulators); goal_misalignment = skippable
  file/deliverable.
- Verifiers: numeric_exact / fact_match / file_written — all deterministic, no LLM judge.
- Over-provisioning: plan in RUNS not tasks; ~120 runs (temp 0.7) to net ~30–38 failing with ≥3–6/class; recommend
  a ~20-run pilot first to measure REAL per-class hit-rates (the stated hit-rates are guesses, not asserted facts).
- Honest weak-spot flags: context_overflow (hardest) and prompt_drift (hard) may resist a disciplined 7B;
  hallucination_loop may convert to honest "not found" (itself a finding); tool_misuse risks being
  environment-driven not model-driven. Surfaced the option of generating starved classes on a messier model
  (e.g. llama3.1:8b) vs accepting thin cells — the human's call.
- 6 open design decisions listed for the human (approve/trim suite; pilot?; label-all-vs-failing-only; HL scoring;
  TM-4 ambiguity; backbone-for-generation fallback).
**Config:** no runs; no code. Backbone still qwen2.5:7b.
**Next:** await human approval/edits on the task spec. Do NOT write the driver or generate traces yet.

---

## 2026-07-21 — Task suite approved; sandbox + fixtures + pilot driver built (NOT run)
**What:** Recorded §6 decisions, then built the kill-test sandbox in code and the pilot driver. Did NOT generate
any traces (awaiting the human's GT/fixture sign-off before generation).
**Why:** Human approved the suite, pilot-first, label-failing-only, HL honesty scoring, no backbone fallback; and
asked to see fixtures + the fact_match normalization rule before approving generation.
**Decisions recorded:** suite approved; TM-4 DROPPED (ambiguous GT encoded a judgment) → 29 tasks; pilot first;
label failing traces only (single labeler); HL = honesty-phrase set; no messier-model fallback (accept thin matrix +
document as scope limit); labeling rubric gains an informal `tm_source` (tool_driven vs model_driven) flag.
**Honest correction:** the earlier doc said "36 tasks" — arithmetic slip; 5 classes × 6 = 30, and after the TM-4 drop
it is **29** (drift 6 / tool_misuse 5 / context_overflow 6 / hallucination_loop 6 / goal_misalignment 6). Fixed in
the doc and encoded in `recovery_sandbox/tasks.py`.
**Result — code built, tests green:**
- New importable package `recovery_sandbox/`: `fixtures.py` (records/search/kv/log/units — all deterministic,
  invariants asserted in tests), `tools.py` (`build_tools(sandbox_dir)` → 10 deterministic tools; errors returned as
  strings; file tools confined to the run sandbox), `tasks.py` (29 TaskSpecs = single source of prompts/tools/
  requirements/verifiers).
- `harness/verifiers.py`: added `all_of`/`any_of` combinators; renamed the normalization helper to public
  `normalize_text` so the search fixture and `fact_match` share ONE rule.
- CO-5 verifier changed from a normalization-fragile fact_match string to `all_of(numeric_exact …)`.
- `paper-recovery/pilot.py`: stratified generator (~20 runs default), saves traces to `data/pilot` (gitignored),
  computes deterministic `answer_correct`, reports failure rate by INTENDED class. **Never labels failure_class**
  (that's the human's). NOT executed.
- `pyproject.toml`: packages now include `recovery_sandbox*`; reinstalled editable.
- **pytest = 63 passed** (added tool determinism/error-path tests AND verifier-vs-fixture GT-consistency tests —
  e.g. #1–6 have exactly 2 Sales, #1–10 have the 5 named departments, log.txt has 3 ERRORs, and each task's CORRECT
  output actually verifies while a hallucinated number fails HL). `py_compile` clean.
**Config:** no live-model runs. Backbone qwen2.5:7b; pilot config `paper-recovery/configs/kill_test.yaml` (temp 0.7,
N=3).
**Next:** show the human the fixtures + normalization rule; on approval, RUN the ~20-run pilot and report the real
failure-by-intended-class rates. Do NOT run the full ~117 batch until pilot rates are in and approved.

---

## 2026-07-21 — Required fixes applied + PILOT RUN (real, low-yield result)
**What:** Applied the 3 required fixes (dropped TM-2 → 28 tasks; TM-1 verifier separate from HL honesty set;
number matching is whole-token not substring) and the HL fabrication rule (honesty AND no invented number). All
tested — **pytest 67 passed**. Then ran the ~20-run pilot on qwen2.5:7b (temp 0.7), one run per task, 4 tasks/class.
**Why:** Measure the REAL failure rate before sizing the full batch (human's pilot-first decision).
**Config:** qwen2.5:7b, temp 0.7, max_turns 12; seed 20260721 (+run offset). 20 runs. Traces at
`data/pilot/traces.jsonl` (gitignored). Code computed deterministic `answer_correct` only — NO class labeling.
**Result — REAL numbers (failure rate by INTENDED class; realized class needs the human's labels):**
- prompt_drift        4 runs, 1 failed (0.25)  — failing: DR-4-r3
- tool_misuse         4 runs, 0 failed (0.00)
- context_overflow    4 runs, 1 failed (0.25)  — failing: CO-1-r8
- hallucination_loop  4 runs, 2 failed (0.50)  — failing: HL-3-r14, HL-4-r15
- goal_misalignment   4 runs, 0 failed (0.00)
- TOTAL: **4 failing / 20 runs (20%)**. All runs stopped at "final" (none hit the turn cap → no loop-type overflow).
**Honest reading (this changes the plan):** qwen2.5:7b is too competent for most of these induction tasks. The two
classes I called "easy/reliable" — goal_misalignment and tool_misuse — produced **ZERO** failures (it wrote every
deliverable and handled every brittle tool). HL (predicted moderate) was the only reliable failure source (2/4,
via fabrication). Extrapolating 20% across the full batch yields failures concentrated in HL/some drift/CO, with
GM & TM starved — i.e. a thin/collapsed recovery matrix, exactly the §5 risk, worse than expected. The 4 failures
are also too few, and n=4/class too noisy, to size anything; and a failing trace's realized class is unknown until
labeled (CO-1 may label as arithmetic slip, not overflow).
**Per decision 6 constraints:** hold the qwen pin; do NOT switch to a messier model; do NOT over-bait tasks.
**Next:** STOP — human decision needed on direction before any more generation: (A) in-bounds difficulty increase
(longer CO chains, lower max_turns to force incompletion, stronger-but-honest drift bait) then re-pilot; (B) accept
a thin matrix, proceed on the classes that fail (HL clearly), document GM/TM/others as hard-to-induce-at-7B scope
limits; or (C) narrow the kill test to inducible classes. Failing traces saved for the human's labeling. NO full
batch, NO auto-labeling.

---

## 2026-07-22 — HL verifier false-negative found + fixed; human labels; confirmatory re-pilot launched
**What:** While preparing the 4 failing pilot traces for the human's labeling, found that HL-3 and HL-4 were
**verifier false-negatives**: the model answered honestly ("did not yield any results", "could not be found") but
the fixed honesty-phrase list didn't contain those phrasings, so honest answers were scored as failures. Replaced
the phrase list with a robust rule and re-ran the confirmatory pilot.
**Why:** A wrong verifier would have put a false "HL is the reliable failure source / 0.50" headline in the paper.
The real pilot failure count is ~2/20, and the model did NOT hallucinate on HL.
**Human labels (their call, decision 4):**
- DR-4 → **hallucination_loop** (asserted a manager name in no tool result instead of calling get_record(77));
  insight: hallucination appeared where drift was intended.
- CO-1 → **completion slip, closest to goal_misalignment** (6 clean adds, no repeat/loop; stopped one operand short).
- Realized distribution over 20: ~1 hallucination, ~1 completion slip; **ZERO** clean context_overflow / tool_misuse /
  deliverable-skip. Human decision: do NOT force a five-class matrix on qwen2.5:7b; expect to REFRAME.
**Fix + changes (all human-approved):**
- **Robust HL rule `no_fabricated_value`** (harness/verifiers.py): correct iff (every number/date in the output was
  in the prompt) AND (no magnitude word hundred/thousand/million/billion/trillion absent from the prompt). No phrase
  list. Credits any honest acknowledgement; fails only on a fabricated figure. Dead phrase list removed.
- **max_turns 12→8** (kill_test.yaml): realistic production tool-call budget; a max_turns stop is tagged
  `stopped_reason="max_turns"` and reported as **budget_exceeded**, kept DISTINCT from context_overflow.
- **Driver (pilot.py):** `--repeats` (default 3), runs all 28 tasks, separates induced_fail vs budget_exceeded in
  the summary; added `stopped_reason` to TraceRecord for labeling.
- **pytest = 69 passed**, incl. regression tests on HL-3/HL-4's exact pilot outputs (now correct) and spelled-out
  magnitude fabrication ("about five million" fails).
**Config:** re-pilot = qwen2.5:7b, temp 0.7, max_turns 8, 84 runs (28 tasks × 3), seed 20260721 + per-run offset;
output data/repilot (gitignored). Launched in background 2026-07-22.
**Next:** on completion, report failure-rate by INTENDED class (induced_fail vs budget_exceeded), save all failing
traces for the human's labeling (no auto-labeling). Then HOLD for the human's scope decision — expected direction:
(B/C) accept a narrow, hallucination-by-skipped-lookup-dominated failure surface and reframe the paper around it +
the iatrogenic-rate question on that surface. NO full batch.

---

## 2026-07-22 — Re-pilot results (84 runs) + TWO MORE verifier artifacts found
**What:** Ran the 84-run confirmatory re-pilot (28 tasks × 3, max_turns 8) and read every induced-failure output.
**Config:** qwen2.5:7b, temp 0.7, max_turns 8, seed 20260721+offset; traces at data/repilot/traces.jsonl.
**Result (deterministic answer_correct; realized class needs human labels):**
- Totals: 11 induced_fail + 6 budget_exceeded of 84. By intended class: prompt_drift 5, context_overflow 3(+3 budget),
  tool_misuse 2, goal_misalignment 1(+3 budget), hallucination_loop **0**.
- **HL fix validated:** 0/18 hallucination on absent-fact tasks — the model honestly acknowledges absence every time.
  The pilot-1 HL "failures" were entirely verifier bugs.
**CRITICAL — two more verifier false-negatives (same rigidity bug as HL), flagged not silently fixed:**
- **TM-3 (2):** model said "could not be found" / "does not exist" — correct handling of a missing file — but GT
  `fact_match("not found")` doesn't substring-match those phrasings → scored wrong. NOT real failures.
- **GM-2 (1):** model wrote a valid 3-row comparison to cmp.txt but formatted rows "1./2./3." instead of "#1/#2/#3",
  so `file_written("#1")` failed on formatting. Deliverable correct → NOT a real failure.
- So **real induced failures ≈ 8, not 11.** Lesson: rigid fact_match/file_written GTs misclassify correct-but-
  differently-worded answers; every string GT needs a hardening/audit pass before a real recovery run.
**Genuine failure surface (observable behavior, not labels):**
- Hallucination-by-skipped-lookup (DR-4 ×2): tool returned manager=#77; model skipped get_record(77) and invented a
  name. The one clear, interesting, real failure mode.
- Date-arithmetic error (DR-6 ×3): fed YYYYMMDD ints to subtract (194) instead of calendar days (56).
- Completion slip / empty final (CO-1 ×3): stopped an operand short or emitted empty output; no looping.
- Budget-exceeded (CO-6 ×3, GM-3 ×3): long tasks hit the 8-turn cap; correctly tagged, NOT overflow.
- Clean context_overflow (loop), tool_misuse (misuse a WORKING tool), deliverable-skip: ~zero real instances.
**Interpretation:** confirms the decision to NOT force a five-class matrix. Realized surface is narrow and centers on
hallucination-by-skipped-lookup. Before any real recovery run, verifiers must be hardened (TM-3 absence check, GM-2
formatting, audit all string GTs) — a ground-truth change = human's call.
**Next:** HOLD for the human's scope decision (expected B/C + re-center on hallucination-by-skipped-lookup and the
iatrogenic-rate question on that surface). Propose verifier-hardening rules for approval. NO full batch, NO
auto-labeling. 17 failing traces saved for the human's labeling.

---

## 2026-07-22 — Verifier adversarial audit + mechanism-level reframe + v2 spec + narrative doc
**What:** Executed three directives + a standing requirement. (1) Built and ran an adversarial verifier battery over
all 28 tasks; (2) reframed the study to the mechanism level; (3) wrote the v2 task-family spec; and created the
synthesized research-narrative document.
**Why:** Three rigid-string verifier false-negatives in a row (HL-3/HL-4, TM-3×2, GM-2) = a systematic ground-truth
risk that silently corrupts every recovery denominator. Audit made top priority. Results also decisively support a
mechanism-level reframe over a five-class matrix.
**Result — Directive 1 (audit):** `recovery_sandbox/audit_battery.py` (147 cases: ≥3 correct phrasings + ≥2 wrong
near-misses per task) + `tests/test_verifier_audit.py` regression guard. **7 mismatches across 4 patterns:**
- TM-3 (3): rigid absence phrasing — "could not be found"/"does not exist"/"no such file" fail fact_match("not found").
- GM-2 (2): rigid `#N` deliverable formatting — "1. Alice…"/"names only" fail file_written("#1").
- CO-4 (1): spelled-out number — "Two records" fails numeric_exact (digit-only).
- DR-5 (1): **false-POSITIVE** — "212 K" (right number, wrong unit) wrongly PASSES numeric_exact(212). Most dangerous
  (under-counts failures).
- HL rule re-verified against the battery: passes all correct paraphrases AND fails fabricated numbers/magnitudes.
Proposed hardened rules (robust absence; name-based deliverable; spelled-number-aware numeric; numeric_with_unit) are
**NOT applied** — ground-truth changes pending human approval. **pytest = 72 passed.** All pilot numbers labeled
PROVISIONAL until hardening is approved/applied and pilots re-scored.
**Result — Directive 2 (reframe):** work-plan.md §2 rewritten to the mechanism spine (skipped-lookup hallucination +
silent tool misuse), with prior two framings kept and marked SUPERSEDED. New §2.0 proposes an operational definition
of **silent tool misuse** and argues DoVer/CausalFlow/CAR are structurally blind to it (no error signal to detect).
paper-recovery/README.md spine updated + PROVISIONAL banner.
**Result — Directive 3 (spec):** `docs/task-family-v2.md` — ~13 skipped-lookup + ~13 silent-misuse tasks with design
axes, per-task hypothesized hit-rates + reasoning, run budgets (~120 to net ~30 failures/mechanism), controls
(anti-guess instruction / right-tool-present / unit-named), and honest manufacturing-risk flags. No code, no traces.
Second-backbone generalization check flagged for AFTER the v2 pilot, not decided.
**Standing:** `docs/RESEARCH-NARRATIVE.md` — full synthesized first version (question, literature+scoop, every
decision with alternatives/why/cost, every result incl. the two verifier corrections, status/limitations). Living
doc; superseded reasoning marked; provisional numbers labeled.
**Config:** no model runs this turn. Backbone qwen2.5:7b.
**Next:** HOLD. Await human approval of (a) the 4 hardened verifier rules, (b) the silent-tool-misuse definition,
(c) the v2 task families. Do NOT apply rules, build fixtures, or generate traces until approved. Then: apply hardened
rules → re-score pilots → build v2 fixtures/verifiers-against-battery → v2 ~20-run pilot.

---

## 2026-07-22 — Battery rebalanced, 4 hardened rules APPLIED, both pilots RE-SCORED
**What:** Human approved the 4 rules with amendments. Rebalanced the battery (≥4 wrong/task, weighted toward wrong
cases), applied the rules, re-ran the audit, and re-scored both pilots.
**Why:** False positives (wrong scored correct) silently inflate recovery rates and reach publication undetected;
false negatives are at least visible. Wrong-case coverage was raised accordingly.
**Applied rules (all human-approved, with amendments):**
- `acknowledges_absence` (TM-3): negation-of-existence AND the fabrication guard AND no ASSERTED content.
- Name-based deliverable (GM-2): checks the three record NAMES; code comment records that this deliberately accepts
  names-without-comparison (a recorded relaxation, not drift).
- `_candidate_numbers` **digits-win-else-spelled**: "Two records" (no digits) matches GT=2, while
  "I called two tools and found 3 in Sales" (digit present) does NOT — the amendment case, now a battery case.
- `numeric_with_unit`: applied to DR-5 (f/fahrenheit), TM-6 (k/kelvin), DR-6 (day/days) after auditing EVERY numeric
  task for unit-ambiguity; the rest are unitless or unit-unambiguous (documented).
**Result — audit:** battery now **199 cases** (87 correct / 112 wrong). Mismatches **7 → 2**. The 2 remaining are
documented RESIDUAL LIMITATIONS, deliberately not patched (patching trades rare false positives for common false
negatives): TM-5 any-number-token can match a correct value used as an INTERMEDIATE while a wrong final is asserted;
CO-5 extra spurious values are not penalized. Recorded in `KNOWN_GAPS`. **pytest = 72 passed.**
**Result — a fix introduced its own bug, caught by re-scoring:** the first `acknowledges_absence` banned any mention
of a content term and wrongly failed the REAL output "…does not exist, so I cannot read its first line" (TM-3-r23).
Rewritten to require an ASSERTION (term + copula + value) so a negated mention passes and the hedge
"…but the first line is probably 'Hello'" still fails. Both real outputs added as permanent battery cases.
**Result — RE-SCORED pilots (5 flips, all false-negatives → correct; none flipped the other way):**
- Pilot 1: induced failures **4 → 2** of 20 (HL-3-r14, HL-4-r15).
- Re-pilot: induced failures **11 → 8** of 84, budget_exceeded 6 (TM-3-r21, TM-3-r23, GM-2-r70 flipped).
  Corrected by intended class: prompt_drift 5, context_overflow 3, tool_misuse **0**, goal_misalignment **0**,
  hallucination_loop **0**; budget_exceeded CO-6 ×3, GM-3 ×3.
- The unit hardening added NO new failures (DR-5 unaffected) — the model did report units correctly.
- **The 8 remaining induced failures are exactly three behaviours:** DR-4 ×2 (skipped-lookup hallucination),
  DR-6 ×3 (silent tool misuse), CO-1 ×3 (completion slip). This corroborates the mechanism-level reframe.
**Status of numbers:** the re-scored counts are **no longer PROVISIONAL**; the 2 residual verifier limitations do
not affect any observed pilot run. Docs updated (RESEARCH-NARRATIVE §4.4/4.6/4.7/§5).
**Next:** HOLD. Show §2.0 (silent-tool-misuse definition) to the human for ratification; await v2 final sign-off.
No v2 traces, no fixtures, no recovery driver until approved.

---

## 2026-07-22 — §2.0 ratified (crit. 4); FIRST recovery kill test run (96 replays, n=8, DIRECTIONAL)
**What:** Amended §2.0 with criterion 4 (false validation) + honest n=3 status. Built the recovery driver
(`paper-recovery/run_recovery.py`), the human labeled the 8 real failing traces, and ran the full cell sweep
(8 traces × 4 interventions × N=3 = 96 replays). First time an intervention was ever applied to a trace.
**Why:** Before scaling v2, measure whether the recovery machinery produces ANY signal (kill test).
**Config:** qwen2.5:7b, temp 0.7, N=3, seed 20260721. Labels (human): DR-4 ×2 hallucination_loop (k=1),
DR-6 ×3 silent_tool_misuse (k=1), CO-1 ×3 goal_misalignment/completion-slip (k=6). Raw:
`data/repilot/recovery/results.json`. Memo: `docs/kill-test-recovery-memo.md`.
**Result — DIRECTIONAL (n=8, NOT a result). Recovery rate by (intervention × mechanism):**
- hallucination(n=2): no_op 0.67 | reflect 1.00 | rollback_2 1.00 | requirement_injection **0.00**
- silent_tool_misuse(n=3): ALL arms **0.00** (incl. no_op) — unrecoverable; no error signal for repair to
  latch onto (corroborates §2.0 gap).
- completion_slip(n=3): no_op 0.00 | reflect **0.67** | rollback_2 0.00 | requirement_injection 0.00
**Key findings:** (1) things MOVE — arms differ from each other and no_op, pattern depends on mechanism (NOT a
null). (2) IATROGENIC CONFIRMED + mechanism verified by re-run: requirement_injection 0/6 vs no_op 4/6 on
hallucination; no_op lets the model spontaneously re-call get_record(#77)→"Priya Nair", while injecting "report
the manager's name" makes it answer immediately with a fabricated name (no further tool call). The intervention
SUPPRESSES the model's own recovery. (3) reflect_and_retry never worse than no_op; only arm that fixes the
completion slip. (4) rollback_2 fixes hallucination but not completion slip (loses partial sums).
**Honest caveats:** n=8 directional; no_op already recovers hallucination 0.67 (easy); silent misuse n=3 one task
shape; near-boundary cells (0.67s) need higher N. Scored by hardened audit-clean verifiers; TM-5/CO-5 residuals
not involved. Verification cost 4 extra replays (data/repilot/recovery_verify).
**Verdict:** recovery premise is ALIVE, not dead — worth scaling to v2. Docs updated (memo,
RESEARCH-NARRATIVE §4.8/§5).
**Next:** HOLD for human. Options: build v2 families (skipped-lookup + silent-misuse) to reach real n; raise N on
near-boundary cells; second-backbone generalization check after v2 shows a real hit rate. No new traces until
approved.

---

## 2026-07-22 — Two protective checks: iatrogenic finding RETRACTED, rollback_2 degeneracy corrected
**What:** Ran the human's two pre-v2 checks. (1) Requirement-phrasing confound: DR-4 (n=2), N=10, 4 phrasings vs
no_op. (2) rollback_2 degeneracy inspection on the 5 k=1 traces. (3) Raised N to 10 on the hallucination cell.
**Why:** Both could invalidate headline claims; resolve before scaling.
**Result — CONFOUND CONFIRMED; iatrogenic framing RETRACTED.** DR-4 recovery (20 replays/arm):
no_op 0.55, reflect 0.90, rollback_2(=restart) 0.60; requirement phrasings — (a) "…report ONLY…" **0.00**,
(b) neutral **1.00**, (c) "…use tools to verify" **1.00**, (d) terse no-'only' **0.30**. The effect does NOT
reproduce across phrasings: the same requirement swings 0.00→1.00 on wording alone. So "requirement injection is
iatrogenic" is WITHDRAWN. What holds: requirement injection is HELPFUL when phrased neutrally/permissively (best
arm, beats reflect), and the surface cue "only" is catastrophic. New, more thesis-aligned finding (agent obeys the
surface wording of the repair, not its intent) → requirement phrasing must be a CONTROLLED FACTOR in the paper,
not one arm.
**Result — rollback_2 degeneracy CORRECTED.** On all 5 k=1 traces (DR-4 ×2, DR-6 ×3), rollback_n(2) clamps to
step 0 with resume-context == initial system+user → functionally `restart_clean`, not a rewind. So "rollback_2
recovers hallucination 1.00" is corrected to "restart of a 2-step task" (≈0.60 at N=10 ≈ no_op). Genuine rollback
only ran on CO-1 (k=6→4), recovered 0.00. The restart_clean-vs-rollback distinction is unmeasured at these short
trace lengths; v2's longer traces will separate them.
**Standing after correction:** interventions move + differ by mechanism (not null); silent tool misuse
unrecoverable by all arms (0/9); reflect robust (never worse than no_op). Two of four first-sweep headline claims
corrected by the checks — honest self-correction, logged.
**Config:** qwen2.5:7b, temp 0.7, N=10 (hallucination); raw data/repilot/phrasing/results.json,
data/repilot/recovery_verify. Docs updated: memo (retraction + phrasing table + rollback note), RESEARCH-NARRATIVE
§4.8.
**Next:** HOLD for human. v2 on hold until they direct; requirement-phrasing now a required v2 factor. No new traces.

---

## 2026-07-25 — Attribution fix, phrasing→primary RQ, rollback_n fixed, v2 BUILT (pilot blocked on Ollama)
**What:** Executed the human's three directives.
**(1) Attribution corrected.** Retracted the "it's the word 'only'" read — (d) has no "only" yet still
underperforms no_op. New working hypothesis (DR-4 only, flagged as such): **imperative action (a,d, below no_op)
vs declarative/permissive constraint (b,c, → 1.00)**; "only" is an intensifier (0.30→0.00). Updated memo +
RESEARCH-NARRATIVE §4.8.
**(2) Phrasing elevated to a PRIMARY research question** in work-plan.md §2 alongside the recovery matrix and the
silent-tool-misuse gap: *"the surface wording of a repair determines whether it works — imperative repairs can be
worse than no repair at all."* Added the program-level convergence note: descriptions (toolseo) and repairs
(recovery) are two surfaces where the same thesis holds.
**(3) rollback_n FIXED (no silent clamp):** at k<n the outcome self-reports as `restart_clean`; added a first-class
`restart_clean` arm. Tests updated (73→ then 81 with v2).
**v2 BUILT (orthogonal design):** `recovery_sandbox/v2_fixtures.py`, `v2_tools.py`, `v2_tasks.py` —
**14 skipped-lookup (SL-01..14)** varying trigger_depth 1/2/3 (detection-lateness), guessable vs opaque targets,
reference types record-chain/related/kv-chain; **13 silent-misuse (SM-01..13)** date-diff/clock-minutes/percent,
some behind a kv lookup. Verifiers on hardened rules, validated per task against correct/wrong/near-miss cases
(`tests/test_v2_sandbox.py`). Every GT cross-checked against fixtures. `pytest = 81 passed`. v2 generation pilot
driver `paper-recovery/pilot_v2.py` (measures hit rate by task/mechanism/trigger_depth; no interventions; no
class labeling).
**Result — v2 PILOT NOT RUN: Ollama server is DOWN** (ConnectionError to localhost:11434; 0 traces). This is the
human's manual step (start Ollama). Everything else is complete and tested.
**Config:** would-be pilot: qwen2.5:7b, temp 0.7, max_turns 8, 27 tasks × 3 = 81 runs → data/v2pilot.
**Next:** human starts Ollama, then runs `python paper-recovery/pilot_v2.py --repeats 3`. Report hit rates by
task shape (and trigger_depth) before the full batch. Then recovery sweep on v2 failing traces with the
phrasing × arm × task-shape crossing. Second backbone still parked (revisit after v2 hit rates; phrasing finding
raises its value). No full batch until hit rates approved.

---

## 2026-07-25 — v2 generation pilot RUN (81 runs); verifiers spot-checked clean; silent-misuse NARROWED
**What:** Human started Ollama and ran the v2 pilot (27 tasks × 3 = 81 runs). Spot-checked 22 traces (11 tasks × 2)
against actual model outputs before trusting the scoring.
**Verifier check — CLEAN (first time no artifacts):** all 22 sampled traces scored correctly. SM-01 fail = genuine
(`subtract(20260915,20260721)=194` reported as 194 days); SM-06/10/13 passes = genuine (model converted 09:15→
decimal hours, "20%"→0.2 correctly); SL chain failures = genuine (model undercounts the chain by one, reports the
depth-(n-1) name); SL-14 kv-chain pass genuine. No false positives (wrong scored correct) or false negatives found.
**Hit rates (n=3/task, DIRECTIONAL):**
- skipped_lookup **0.71** (30/42). Clean MONOTONIC detection-lateness trend: depth0 0.54, depth1 0.54, depth2 0.80,
  depth3 1.00. Related-record tasks (SL-08/10/11) 1.00; depth≥2 manager chains 1.00; depth-1 guessable manager
  (SL-01) 0.00 (weak); opaque depth-1 (SL-04/12) ~0.33.
- silent_tool_misuse **0.49** (19/39) — but this HIDES a sharp split: **DATE tasks (SM-01..05) 5/5 at 100%**;
  **CLOCK (SM-06..09) and PERCENT (SM-10..13) ~0%** (model converts correctly, does NOT misuse).
**Key finding — silent tool misuse is NARROWER than §2.0 implied:** it reliably reproduces only for a semantic type
with a plausible integer encoding (dates as YYYYMMDD). The model correctly converts times and percentages. Reframe
as **date-arithmetic silent misuse**; clock/percent become CONTROLS proving the misuse is SELECTIVE, not blanket —
which strengthens the characterization while narrowing the class. §2.0 evidential status updated.
**Config:** qwen2.5:7b, temp 0.7, max_turns 8; 0 budget_exceeded (all tasks fit the budget). 49 failing traces at
data/v2pilot/traces.jsonl (30 skipped_lookup + 19 silent_misuse), saved for human labeling + the recovery sweep.
**Next:** HOLD for human approval of the full batch. Recommendations: SL — keep, drop/deprioritize SL-01 (weak),
depth axis works for detection-lateness; SM — keep the 5 date tasks as the misuse inducers, KEEP clock/percent as
explicit controls (do not treat as inducers). Then recovery sweep on labeled v2 failures with phrasing × arm ×
task-shape. No full batch or second backbone until approved.

---

## 2026-07-25 — Surface-form boundary probes + FULL v2 batch (186 runs); silent misuse is BROAD
**What:** Added 4 surface-form boundary probes (SF-01..04) and ran the full v2 batch (31 tasks × 6 = 186 runs).
Spot-checked SF + clock + SL traces before trusting scoring.
**BOUNDARY VERDICT — the trigger is SURFACE FORM, not dates (broad class).** Verified from actual tool calls:
- SF-01 `HHMM` → `subtract(1430,915)=515`; SF-02 → `subtract(1305,1045)=260`; SF-04 version → `subtract(2.11,2.9)=-0.79`
  — all MISUSED. SM-06 `HH:MM` → converts to decimal hours first (315, CORRECT). SF-03 control (subtraction is
  right) → 194, CORRECT.
- So the class is **"surface-form-mimics-operand"**: the model applies a general tool whenever the input's surface
  form looks like the operand (bare integer/dotted number), even when semantics need conversion; converts correctly
  only when the form is structurally marked (colon). Broader/stronger than "date-arithmetic". §2.0 updated.
**CAVEAT (logged, not hidden):** the aggregate silent_misuse rate (0.54) is polluted — HH:MM clock tasks that fail
(SM-07 `add(75,80)=155`; SM-08 `(19+30-7)*60=2520`) fail via MUDDLED reasoning, not the clean mechanism. CLEAN
inducers = date (SM-01..05), HHMM (SF-01/02), version (SF-04). Colon clock = noise; percent + SM-06 + SF-03 =
selectivity controls. Verifiers spot-checked CLEAN (no artifacts; SF-01 slightly noisy via self-correction, a known
numeric_with_unit any-token residual).
**Hit rates (n=6/task, DIRECTIONAL):** skipped_lookup 0.65 (55/84); silent_tool_misuse 0.54 (42/78);
surface_form_probe 0.71 (17/24). Skipped-lookup detection-lateness (within-mechanism): depth1 0.52, depth2 0.80,
depth3 1.00 — clean monotonic. SL failure mode verified = report the intermediate/own entity, skip the next lookup
(SL-08). Weak SL tasks: SL-01/12/14 (0.00; model does the lookup / handles kv-chain). Date misuse 5/5 ~100%.
**Config:** qwen2.5:7b, temp 0.7, max_turns 8, 0 budget. **114 failing traces** at data/v2batch/traces.jsonl
(SL + date-misuse + SF). pytest 82 passed.
**Next:** HOLD. Present failing traces grouped by trigger_depth for human labeling (k = step the lookup was skipped;
RQ3 lives there). Then recovery sweep with phrasing × arm × task-shape × depth on the CLEAN pools. Second backbone
after recovery confirmed on qwen. No sweep until human labels + approves.

---

## 2026-07-25 — Ambiguous-group scoring audit; labeling view + buckets; root README + LICENSE
**What:** Per-trace scoring audit of the groups the human flagged, regenerated the labeling artifacts with factual
bucket hints, and created the root README.md + Apache-2.0 LICENSE.
**Audit result (verifiers SOUND — no false pos/neg; the issue is class-MIXING inside answer_correct=False):**
- SM depth-0 (dates IN PROMPT, SM-02/03/04): cell collapses — ~1 clean misuse (SM-02-r92); the rest are REFUSALS
  ("None of the provided functions can calculate days between dates" → goal_misalignment) and MUDDLED reasoning (gap).
- SM depth-1 (dates via kv_lookup, SM-01/05): CLEAN 12/12 (subtract on YYYYMMDD → 194/80). **Finding: the misuse
  fires when the date ARRIVES AS A TOOL RESULT, not when stated in the prompt** — tool-returned data primes "keep
  feeding tools"; prompt-stated data invites reflection/refusal.
- SL-04-r23: honest INCOMPLETE (reported the manager ID, refused to invent) → goal_misalignment, not the mechanism.
- SL-07: mixed — r37 clean skip (own dept), r39 HALLUCINATION ("Sales", absent from all tool results), r40 refusal.
- SF-04 (version): the surface-form TRIGGER fires (subtract 2.11-2.9=-0.79) but outputs are muddled (0/1/8/0.79) —
  NOT clean; version is a noisy inducer → gap.
**Re-sorted pools (bucket counts over 114 failing):** clean surface-form ≈ 13 date-subtract + 10 hhmm ≈ 23 (not 46);
skipped_lookup candidates ≈ 52 skip-or-assert (gr1 24 / gr2 22 / gr3 6) minus scattered hallucination/incomplete;
plus 10 refusals + 24 muddled to be labeled as their own classes. Pool shrank and re-sorted, as the human predicted.
**Artifacts:** `data/v2batch/labeling_view.md` (ALL 114 failing traces, grouped by mechanism×depth, each with a
factual `bucket=` hint — clean-date-subtract / clean-hhmm-subtract / REFUSAL / INCOMPLETE / skip-or-assert(gr=N) /
muddled — NOT a class) + `labels.template.json`.
**README + LICENSE:** wrote a professional root `README.md` (honest per CLAUDE.md §5 — aggregate/method only, raw
data noted as local-only, findings labeled DIRECTIONAL/small-n, retractions acknowledged) and `LICENSE` (Apache-2.0,
Copyright 2026 Ayush Singh).
**Next:** human labels per-trace from the view (class + k, flag gap/hallucination/goal_misalignment/unclear). Then
recompute compute-plan per-cell n from the LABELED clean pool and show before running the recovery sweep. No sweep,
no second backbone until then.


---

## 2026-07-27 — v2 RECOVERY SWEEP run (1692 replays); DR-4 hypothesis corrected -> action-licensing
**What:** Validated codex's labels.json (clean; 1 flag was a validator false-alarm; BOM stripped), built +
dry-checked the v2 recovery driver (paper-recovery/run_recovery_v2.py, 8 arms + per-task requirement cores),
human ran the full sweep (81 traces, 8 arms, N=3 = 1692 replays), then I broke it down by depth/form and
spot-checked replays with full output capture before trusting it.
**Verifiers:** spot-check confirmed the numbers reflect real behavior (genuine extra get_record on recovery,
genuine no-lookup re-assertion on failure); no false positives found.
**RESULT 1 (skipped_lookup, n=50, depths 1-3) — recoverable; DR-4 imperative/declarative REFUTED:**
- Recovery by arm x depth: reflect 0.75/0.79/0.89; declarative_lookup_permitting 1.00/0.83/0.39;
  imperative_plain 0.62/0.51/0.00; imperative_only 0.67/0.12/0.00; declarative_neutral 0.24/0.29/0.00;
  rollback_2/restart_clean 0.25/0/0; no_op 0.03/0/0.
- declarative_NEUTRAL is among the WORST (below imperative_plain) -> "declarative>imperative" (DR-4) is refuted.
  Driver is ACTION-LICENSING: arms that explicitly license the corrective step (lookup_permitting "use tools to
  verify"; reflect "review your work") recover; bare constraint/command does not. RQ3 lateness present (recovery
  degrades with depth). No iatrogenic harm on skipped_lookup.
**RESULT 2 (surface_form_misuse, n=31) — recovery-RESISTANT:**
- date (n=13) and hhmm (n=11) misuse resist EVERY arm (<=0.15). No text repair removes the tool's false
  validation (corrupting signal is a tool result, not a prompt) -> confirms/sharpens the s2.0 gap at real n.
- version (n=6) noisy outlier (no_op already 0.28); carries no weight.
**Caveats:** DIRECTIONAL, single model, N=3; 119 near-boundary cells (mid-range rates need higher N; extremes are
robust); reflect/rollback/restart on n=8/8/6 breadth subset.
**Docs:** docs/recovery-v2-results.md (full memo+tables); RESEARCH-NARRATIVE s4.10; work-plan phrasing RQ refined
to action-licensing. Raw: data/v2batch/recovery_v2/results.json.
**Next:** HOLD for human. Options: (1) raise N on near-boundary mid-range cells; (2) SECOND-BACKBONE generalization
check is now SEQUENCEABLE (recovery confirmed on qwen) -> replicate "action-licensing recovers skipped-lookup" and
"surface-form misuse is recovery-resistant" on a 2nd model. Two DR-era claims now corrected (iatrogenic->phrasing;
imperative/declarative->action-licensing) - both logged, not hidden.
