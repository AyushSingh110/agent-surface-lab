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

