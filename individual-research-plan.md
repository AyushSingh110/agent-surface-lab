# Individual Research Line — Deep Analysis of Five Ideas

*A working document. Everything here is a starting frame, not a fixed plan. The novelty claims are current as of mid-2026 but this area moves fast — re-check arXiv listings from the last ~3 months before you commit to any single idea.*

---

## How to read this document

You asked for detail on five ideas, plus which one I'd pick, plus how I'd actually build it (Claude Code and tooling), plus how to run the GitHub side. This document is in four parts:

1. **The five ideas, worked up in full** — problem, research questions, hypotheses, method, baselines, metrics, novelty risk, feasibility, and target venues for each.
2. **Are these one project or five?** — the strategic question, because it changes everything downstream.
3. **What I'd do in your place** — the pick, and *why*.
4. **The build process** — step by step, with Claude Code, plus the GitHub strategy (public vs private, what to hide, when to flip it).

One framing note before the ideas. All five sit on a single spine: **agents act on surface text and surface cues rather than on the deeper thing the cue is supposed to represent.** Descriptions instead of capability. The word "delete" instead of actual consequence. A detected failure instead of a recoverable one. That's not a coincidence — it's the thesis of a research *program*, and it's why these belong together even though each is a separate paper. Keep that sentence in your head; it's the through-line that makes a committee (and later, a PhD application or a hiring manager) see a researcher rather than a person who did five unrelated demos.

---

# PART 1 — THE FIVE IDEAS

---

## Idea A — Recovery, not detection: what actually fixes a failing agent run?

### The problem, and why it hurts in production

Every paper in the agent-failure space stops at the same place: "we detected the failure / attributed it to agent 3 at step 7." Then it ends. But the question a production on-call engineer actually has at 2am is the *next* one: **now that I know it's failing, what do I do about it, and will doing something make it better or worse?**

This is a real and expensive gap. Teams bolt on "reflect and retry" or "self-correction" loops on the assumption that intervening helps. That assumption is mostly untested at the level of *which intervention works on which failure*. It is entirely plausible — and this is the bet — that generic reflection is net-harmful on some failure classes (it rationalizes the wrong answer more fluently), while a blunt rollback would have worked. If that's true, a lot of production self-correction machinery is actively hurting.

### Research questions

- **RQ1.** Given a failure detected at step *k*, what is the recovery rate of each intervention type, broken down by failure class?
- **RQ2.** What is the *iatrogenic rate* — the fraction of cases where intervening produces a worse outcome than doing nothing (letting the run finish uncorrected)?
- **RQ3.** How does recovery rate decay as a function of *detection lateness* — i.e., how much does it cost you to catch the failure at step 8 instead of step 3?
- **RQ4.** Is there a cheap *policy* — a mapping from (failure class, step) → best intervention — that beats always-reflect and always-rollback?

### The key design move (this is what makes it a study and not a demo)

You measure recovery **causally, by counterfactual replay**, not by asking an LLM judge whether the fix "looks better." Because you have recorded traces, you can:

1. Take a run that failed.
2. Rewind to the detected failure step *k*.
3. Apply intervention *I* (re-anchor prompt / rollback to *k−2* / force tool re-call / inject the missing requirement / restart clean / escalate).
4. Re-run forward from that point.
5. Check the *actual* final outcome against ground truth (did the file get written? was the fact correct?).

This is a genuine counterfactual, not a judgment. That's the methodological backbone and it's what a reviewer will respect.

### The intervention taxonomy (one axis) × failure taxonomy (other axis)

| Intervention | What it does |
|---|---|
| **No-op** (control) | Let the run finish. The baseline every other cell is measured against. |
| **Re-anchor** | Re-inject the original goal into context at step *k*. |
| **Rollback-*n*** | Rewind *n* steps and resume (try *n*=1,2,3). |
| **Tool re-call** | Force a repeat of the last tool call, possibly with corrected args. |
| **Requirement injection** | Explicitly hand the agent the requirement it missed. |
| **Reflect-and-retry** | The standard "critique your own work and redo" — the incumbent you're testing. |
| **Restart-clean** | Throw the trajectory away, start the task fresh. |
| **Escalate** | Stop and hand to a human (models the "give up" option). |

Cross that with failure classes (drift, tool-misuse, context-overflow, hallucination, goal-misalignment) and you get a **recovery matrix**. The paper *is* that matrix, plus the story it tells.

### Hypotheses (my priors — worth stating so you can be surprised)

- **H1.** Late-detected `goal_misalignment` is essentially unrecoverable without rollback. Re-anchoring won't help because the agent already "thinks" it's done.
- **H2.** `tool_misuse` recovers cheaply with tool re-call — it's the easiest cell in the matrix.
- **H3.** Reflect-and-retry has a **positive iatrogenic rate on hallucination** — the agent reflects itself into more confident wrongness. If this holds, it's your headline, because it contradicts a widely assumed-good technique.
- **H4.** Recovery rate decays sharply with detection lateness — motivating *early* detection (which is exactly Idea B, so the two papers hold hands).

### Baselines

Always-no-op (do nothing), always-reflect (the incumbent), always-rollback, and a random intervention policy. Your learned/rule-based policy has to beat all four to be worth anything.

### Metrics

Recovery rate (per cell and overall), iatrogenic rate, net improvement over no-op, token/step cost of each intervention, and a cost-adjusted "recovery per dollar."

### Novelty risk — **LOW to MODERATE**

The failure-*detection* and failure-*attribution* space is saturated (Who&When Pro alone is 12k+ traces). But **recovery efficacy as a systematic, counterfactual study is a genuine gap** — the field has been so busy detecting that almost nobody has measured whether detection is *actionable*. The negative-result angle ("detection is not repair") is exactly the kind of finding Q1 venues take because it corrects a field-wide assumption. Risk is that a bigger lab publishes something adjacent while you work; mitigate by scoping tight and moving fast.

### Feasibility — **HIGH**

Weeks, not months, for a first signal. You need: recorded failing traces with ground truth, a replay harness, and the eight interventions implemented as functions. Free Groq/Ollama inference is enough. One agent scaffold, two model backbones — resist expanding.

### Target venues

ICLR / NeurIPS workshops (Agentic AI, R0-FoMo-style reliability tracks), ACL Demo/Findings, or a solid arXiv preprint that a systems venue (MLSys) would like. The negative-result framing plays well in workshop settings that value "things the field got wrong."

---

## Idea B — Predictive failure as a decision problem

### The problem

Can you tell a run is going to fail *before* it finishes, early enough to do something about it (see Idea A)? The naive version — "train a classifier to predict failure, report F1 at step 3" — is a trap. Reviewers have seen a hundred of those and they're boring, because an F1 number doesn't tell anyone *when to act*.

### The reframe that makes it publishable

Frame it as **cost-aware early stopping**, borrowed straight from sequential decision theory. At each step you hold a *posterior probability of eventual failure* and you face a choice: keep going (costs tokens/time, might recover) or abort/intervene now (saves cost, but might kill a run that would've succeeded).

The output is not an accuracy number. It's a **Pareto frontier**: tokens-saved on the x-axis, correct-runs-killed on the y-axis. Then you derive the operating regimes where early abort *dominates* letting the run finish. That's an economics-of-agents result, and it's the kind of thing people actually deploy.

### Research questions

- **RQ1.** How early, and how reliably, can eventual failure be predicted from partial trajectory features?
- **RQ2.** What's the Pareto trade-off between compute saved and good runs killed, as a function of the abort threshold?
- **RQ3.** Under what cost structures (cheap vs expensive inference, high vs low stakes) does early abort beat run-to-completion?
- **RQ4.** Which trajectory features carry the predictive signal — and do they transfer across task types and model backbones?

### Method

Take runs with per-step traces. Truncate each at step *k*. Featurize the partial trajectory: embedding-drift from the goal, tool-error density, step-repetition, self-contradiction signals, confidence markers, output-length dynamics. Train a lightweight predictor (logistic reg / XGBoost — you already know XGBoost from ARIA) to output P(eventual failure | trajectory up to *k*). Then wrap it in a decision rule with an explicit cost model and sweep the threshold to trace the Pareto curve.

### Hypotheses

- **H1.** Loop-type failures (context-overflow, tool-error loops) are predictable *early* — the signal is in repetition. Outcome-type failures (goal-misalignment) are predictable only *late*, because they look fine until the end. This asymmetry is itself a finding.
- **H2.** Agents are **not elastic to the prediction** — knowing failure is likely doesn't help unless you pair it with a working intervention (which is why B needs A).
- **H3.** A simple feature set (drift + repetition + error density) captures most of the predictive signal; the fancy stuff adds little.

### Baselines

Predict-never (run everything to completion), predict-always-fail (abort everything — absurd but bounds the axis), a length-only heuristic, and an LLM-judge-at-step-*k* asked "is this going well?"

### Metrics

Pareto curve (the headline), AUROC/AUPRC per failure type per step, earliness (steps saved before the true failure manifests), and net cost saved under several cost models.

### Novelty risk — **MODERATE**

Failure prediction exists; the *decision-theoretic, cost-aware* framing is much less crowded and is where the contribution lives. The risk is presentation: if you slip back into "here's my classifier's F1," it's a rejected paper. The Pareto/economics framing is non-negotiable.

### Feasibility — **HIGH**

You may already have the data if Idea A's harness records per-step traces. Truncate, featurize, train, sweep. This is the cheapest of the five in raw effort.

### Why A and B are one paper (or a tight pair)

*Predict failure early (B) → intervene (A) → verify the intervention actually recovered the run (A).* That's a complete, coherent arc: **prediction → action → causal verification.** It's the natural continuation of your ARIA line and it fills the exact hole every detection paper leaves open. If you want one strong paper instead of two thin ones, this is it.

---

## Idea C — Tool-description as an adversarial surface ("SEO for agents")

### The problem

Two Feb-2026 studies set this up but didn't chase the consequence. One found the overwhelming majority of MCP tool descriptions have quality defects and most never say *when* to use the tool. The other, across ten-thousand-plus servers, found that tools with better-written descriptions get selected far more often *when multiple servers offer the same capability.*

Read that second finding as an economist: **in a competitive registry, description text — not actual capability — drives selection share.** As tool registries become marketplaces (which is happening now), that creates a direct incentive to optimize descriptions to *win routing regardless of whether your tool is better.* This is SEO, reborn for the agent era, and nobody has studied it as a strategic/adversarial system.

### Research questions

- **RQ1.** Holding capability *identical*, how much selection share can be bought purely by optimizing description text? (The "routing hijack rate.")
- **RQ2.** How does the hijack scale with the number of competing tools, and across model backbones?
- **RQ3.** Does hijacking *persist* after the inferior tool visibly fails — does the agent learn, or keep re-selecting the well-described dud?
- **RQ4.** What defenses work — capability-grounded selection, execution-outcome reputation, description normalization — and what do they cost in accuracy/latency?

### The three-act structure (attack → measurement → defense)

This is why C is strong: it has the shape reviewers like.

- **Act 1 (attack).** Build a registry with *matched tool pairs*: same underlying function, one honest description, one adversarially optimized. Your optimizer can literally be a DSPy program (you know DSPy from ARIA) that maximizes selection probability — the attacker is a few lines.
- **Act 2 (measurement).** Measure hijack rate across backbones and competitor counts. Include a *malicious* variant: an inferior or even harmful tool that wins routing via description alone — that's the security stinger.
- **Act 3 (defense).** Propose and evaluate mitigations. Show the trade-off curve, not just "our defense works."

### Hypotheses

- **H1.** You can move selection by 20+ points on capability-identical tools with description text alone. (If the kill-test below doesn't show at least this, pivot.)
- **H2.** The hijack *worsens* as competitor count grows — more near-misses, more room for text to tip the choice.
- **H3.** Agents mostly **don't** learn from a well-described tool failing; they re-select it, because selection is a fresh text-matching decision each turn with no memory of the dud. This is the scary result and the reason a defense is needed.
- **H4.** Outcome-based reputation is the only defense that generalizes; pure text normalization is beaten by a better attacker.

### Baselines / comparisons

Honest-description routing, random routing, retrieval-based (Tool-RAG-style) routing — and show that Tool-RAG *doesn't* fix this, because retrieval also runs on description text, so it's hijackable too. That's a nice "the existing fix doesn't help here" beat.

### Metrics

Routing hijack rate, selection-share delta, hijack-persistence-after-failure, attack-success under each defense, and defense cost (accuracy/latency/token overhead).

### Novelty risk — **LOW**

This is the freshest of the five. The setup studies exist but the *adversarial/strategic/marketplace* framing with an attack-and-defense is open, and it only gets more relevant as agentic commerce and tool marketplaces grow. Security framing also insulates you somewhat — security venues move differently from the eval treadmill.

### Feasibility — **HIGH**

Fully synthetic registry, small models, no human labeling, laptop-scale. The DSPy attacker is the clever part and it's cheap.

### Target venues

Security-flavored ML venues, agent-security workshops, ACL/EMNLP (they like attack/defense on LLM systems), or a strong arXiv preprint. This one has the best "surprising and quotable" headline of the five.

---

## Idea D — Do agents know what they can't undo?

### The problem

Production teams are genuinely scared of agents that send, delete, transfer, publish, or push. The standard mitigation is a human approval gate on a hardcoded allowlist of "dangerous" actions. Nobody has asked the *behavioral* question underneath: **does the model itself internally represent irreversibility, and does it modulate caution accordingly — or is it just reacting to scary-sounding words?**

If caution tracks the word "delete" rather than the actual consequence, then a tool named `cleanup()` that hard-deletes is a landmine, and the entire allowlist approach is resting on lexical luck.

### Research questions

- **RQ1.** Do agents behave more cautiously (verify, ask, hesitate) before irreversible actions than before matched reversible ones?
- **RQ2.** Is that caution driven by *consequence* or by *surface lexical cues*? (The core question.)
- **RQ3.** Does caution survive adversarial framing — a benign-sounding name that hides an irreversible effect, or time pressure injected into the prompt?
- **RQ4.** Can you cheaply *induce* consequence-awareness (a system-prompt intervention, a reversibility field in the tool schema) and does it hold up under paraphrase?

### Method

A sandbox of **matched action pairs** — same surface form, opposite reversibility:

| Reversible | Irreversible |
|---|---|
| `save_draft` | `send_email` |
| `archive` | `delete` |
| `stage_changes` | `commit_and_push` |
| `add_to_cart` | `place_order` |
| `preview` | `publish` |

Then two adversarial manipulations: (a) **name masking** — give the irreversible action an innocuous name (`cleanup`, `finalize`, `sync`) and see if caution evaporates; (b) **pressure** — inject urgency ("the user is waiting, be fast") and measure whether verification behavior degrades.

Measure: does the agent verify args, ask for confirmation, hesitate, or double-check before pulling an irreversible trigger — and how that rate shifts across the manipulations.

### Hypotheses

- **H1.** Caution tracks **lexical cues, not consequence.** `delete` triggers care; `cleanup` (same effect) does not. This is the likely headline and it's directly actionable.
- **H2.** Name-masking substantially reduces caution — a straightforward, alarming demonstration.
- **H3.** Injected time pressure reduces verification, i.e., "safety" behavior is fragile under exactly the conditions (urgency) where it matters most.
- **H4.** A reversibility field in the schema helps, but only if the model is prompted to attend to it — it doesn't emerge for free.

### Baselines

Reversible actions (the within-pair control), and a no-manipulation condition against the masked/pressured conditions.

### Metrics

Verification rate, confirmation-seeking rate, hesitation/hedging markers, and the *drop* in each under masking and pressure. The deltas are the finding.

### Novelty risk — **LOW to MODERATE**

Connects to the AI-safety and tool-safety literature without needing frontier-model access. The specific "consequence vs lexical cue" dissociation, done cleanly with matched pairs, is underexplored. Some risk that a safety lab has an unpublished version; check recent listings.

### Feasibility — **HIGH**

Sandboxed, no ethics review, no user study, small models fine. Arguably the cleanest single-result paper of the five — one crisp, memorable finding.

### Target venues

Safety/alignment workshops (SafeGenAI-style), ACL/EMNLP short paper, or a focused arXiv preprint. Pairs naturally with Idea C under the "agents act on surface text" thesis.

---

## Idea E — Anytime agents: what do you get if you pull the plug at 60%?

### The problem

Classic *anytime algorithms* always hold a valid best-so-far answer — interrupt whenever and you get something usable. LLM agents don't work like that. Interrupt one mid-run and you typically get **nothing** — a half-parsed plan, no answer. That's why agents and hard latency SLAs mix badly in production: you can't safely time-box them.

### Research questions

- **RQ1.** What is the **partial-value curve** — as a function of fraction-of-budget consumed, how useful is the agent's state if forced to answer *right now*?
- **RQ2.** Is that curve smooth (graceful degradation) or a cliff (all value arrives in the last step)?
- **RQ3.** Does **budget-conditioning** ("you have 4 tool calls, then you must answer") flatten the curve — i.e., can agents be made elastic to a stated budget?
- **RQ4.** Does maintaining an explicit *running best answer* recover partial value, and what does it cost at full budget?

### Method

Run agents on tasks, then forcibly interrupt at *f* ∈ {20%, 40%, 60%, 80%} of budget and extract whatever answer can be salvaged. Score salvaged answers against ground truth to build the partial-value curve. Then compare three regimes: vanilla, budget-conditioned prompt, and maintained-running-answer.

### Hypotheses

- **H1.** Vanilla agents show a **cliff** — near-zero usable value until the final step, because they don't checkpoint an answer.
- **H2.** Agents are **not elastic** to stated budgets — told "you have 4 calls," they plan roughly the same and just get truncated, rather than front-loading the answer. (This mirrors H2 in Idea B — the "agents don't adapt to stated constraints" motif recurs, and that recurrence across papers is itself a nice program-level observation.)
- **H3.** A maintained running answer flattens the curve meaningfully, at a modest full-budget quality cost.

### Baselines

Vanilla run-to-completion, random truncation, and an "always emit current best guess" wrapper.

### Metrics

Partial value at each interruption fraction, area-under-the-partial-value-curve, elasticity (slope of value vs stated budget), and full-budget quality cost of each intervention.

### Novelty risk — **UNVERIFIED / MODERATE**

I flagged this before and I'll flag it again: I did **not** novelty-check E as carefully as A–D. The anytime-computation framing applied to LLM agents feels underexplored, but "test-time compute" and "budget-aware inference" are hot, so something adjacent may exist. **Do a dedicated search before you touch this one.** Treat it as the highest-uncertainty idea on novelty.

### Feasibility — **HIGH** (engineering), **MEDIUM** (novelty)

The interruption harness is easy. The risk isn't building it; it's finding out someone published it in March.

### Target venues

MLSys / efficiency workshops, ICLR workshops on test-time compute, or arXiv.

---

# PART 2 — ONE PROJECT OR FIVE?

**One shared harness. Several separate papers. Never one mega-system.**

Why not one big system: reviewers reward a paper that answers *one* question cleanly and punish a paper that answers four partially. "We built a platform that audits tool descriptions, tests irreversibility, and does anytime interruption" reads as a product demo with no finding. Each idea needs its own crisp headline sentence.

Why one shared harness: the engineering under A, B, D, and E is nearly identical — a sandbox with instrumented tools, a trace recorder, a replay/interruption layer, and a metrics module. Build that **once, well**, and every subsequent study costs weeks instead of months. That reusable harness is the real compounding asset of your research line — more than any single paper.

So the structure is: **one repo, one infrastructure, sequential focused studies.** A+B ship as the first paper (they're a natural pair). C and D are the second and third, cheap because the harness already exists. E is optional and gated on a novelty check.

The unifying thesis that ties all five into a *program* (say this in every intro): **LLM agents act on surface text and surface cues rather than the deeper property those cues represent** — descriptions over capability (C), words over consequence (D), detection over recoverability (A), stated budgets they don't actually adapt to (B, E).

---

# PART 3 — WHAT I'D DO IN YOUR PLACE

**I'd build the shared harness, then ship A+B as the first paper, then C as the second.**

Reasoning, ranked by what actually matters for a first serious publication:

1. **A+B is the safest strong bet and it's *yours*.** It's the direct continuation of ARIA, so your existing skills and even some existing code transfer. The "detection is not repair" finding corrects a field-wide assumption, which is exactly the profile of a paper that gets in despite not having a frontier-lab GPU budget. And the causal-replay method is defensible in a viva — you're not hand-waving with an LLM judge.

2. **C is the highest-*upside* idea** — freshest, best headline, security framing that dodges the eval treadmill. I put it second only because it's slightly riskier to land than A+B and because doing A+B first gives you the harness and the confidence. If you're feeling bold, you could invert this and do C first. Both are defensible.

3. **D is the best *single-afternoon-to-signal* idea** and a great third paper or a great "we also found" section. One clean finding, memorable, cheap.

4. **E I'd hold** until you've novelty-checked it. Good idea, unverified ground.

If I could only publish one thing this year: **A+B.** If I wanted the one most likely to get quoted on tech Twitter: **C.**

---

# PART 4 — HOW I'D ACTUALLY BUILD IT

This is the part that separates "good idea" from "submitted paper." Here's the concrete process, tooling included.

## 4.1 — The two-week kill test (do this *before* committing to anything)

Do not build infrastructure first. For whichever idea you pick, run the cheapest possible experiment that could *disprove* your central hypothesis. If it survives, you have a paper. If it dies, you saved yourself six months.

- **For A+B:** take ~30 existing failing traces, hand-implement 3 interventions at the failure step, replay, count recoveries. If recovery rates differ sharply across failure classes → paper. If they're all the same → pivot.
- **For C:** build 10 matched tool pairs, optimize one description in each with a simple LLM loop, measure selection-share shift on 2 backbones. If you can move selection 20+ points on capability-identical tools → headline. If not → pivot.
- **For D:** build 5 matched action pairs, run masked vs unmasked, eyeball whether caution drops. If masking kills caution → paper.

Write the kill-test result up in a one-page memo *regardless of outcome*. That memo is the seed of your intro.

## 4.2 — Phased build (after the kill test survives)

**Phase 0 — Harness (week 1–2).** The reusable core: a sandbox that registers instrumented tools, a runner that executes an agent scaffold against a task, a trace recorder (every step, tool call, arg, result, timestamp), a replay layer (resume from step *k*), and a metrics module. Pin one agent scaffold, two backbones (one Groq-hosted large, one Ollama local). **Resist making this a framework.** It serves your experiments, nobody else's.

**Phase 1 — Data / task set (week 2–3).** Curate or generate the tasks with *ground truth* (you need to know the true outcome to score anything). For A+B, reuse ARIA-style traces. For C, build the synthetic registry. Keep it small and clean over large and noisy.

**Phase 2 — The experiment (week 3–6).** Implement the interventions / attacks / manipulations as clean, swappable functions. Run the full matrix. Log everything to disk in a format you can re-analyze without re-running (this saves you enormously).

**Phase 3 — Analysis (week 6–8).** Build the headline figure *first* (the recovery matrix / the Pareto curve / the hijack-rate plot) and let it tell you whether the story holds. Then baselines, ablations, robustness (across backbones, across paraphrases).

**Phase 4 — Write-up (week 8–12).** Intro from your kill-test memo, method, results around the headline figure, limitations (be honest — reviewers trust honest limitations), related work. Target a workshop deadline first; a workshop paper de-risks the full submission.

## 4.3 — Using Claude Code (and the rest of the toolchain)

You have Claude Code — use it for the *engineering*, not the *science*. The division of labor that works:

- **Claude Code builds the harness.** Trace recorder, replay layer, tool-registry sandbox, metrics module, plotting scripts, the DSPy attacker for C. This is exactly the kind of well-specified, testable engineering it's good at. Give it the interfaces and let it fill them in, with tests.
- **You own the experimental design, the hypotheses, and the interpretation.** Claude Code will happily implement a flawed experiment perfectly. The judgment calls — what's a fair baseline, is this confound controlled, does this result actually support the claim — stay with you. That's the research, and it's what your name is on.
- **Use Claude (chat, this one) for the thinking-out-loud:** poking holes in your design before you run it, drafting the intro, checking whether a result is surprising or trivial, and — critically — **novelty-checking against recent arXiv before and during** the project so you don't get scooped or duplicate.
- **Keep a lab notebook.** A running markdown log of every experiment: hypothesis, config, result, what surprised you. This is gold at write-up time and it's what makes the work reproducible. Claude Code can even scaffold a script that auto-appends run metadata to it.

A concrete first session with Claude Code looks like: "Build me a trace recorder that wraps an agent runner and logs, per step: the tool called, args, result, timestamp, and a monotonic step index, to a JSONL file. Include a replay function that reconstructs state up to step *k* and resumes. Write pytest tests for both." Then iterate. You review, you don't just accept.

## 4.4 — GitHub strategy (public vs private, and when to flip)

Short version: **start private, go public with the code at submission, keep the sensitive assets private forever.**

**Keep private (the whole time, and even after publishing):**
- **Raw datasets, labeled traces, and full analyses** — exactly as your ARIA README already does ("raw datasets, labeled traces, and full research analyses are not included"). This protects your ability to extend the work and prevents someone from re-running your exact study before you've mined it. Ship *aggregate numbers and the method*, not the raw research assets.
- **Unpublished experiment logs and the lab notebook.**
- **Anything that constitutes a working attack** *until* you've published the defense alongside it. For Idea C especially: don't open-source a routing-hijack optimizer with no mitigation attached — pair attack and defense in the same release. Responsible disclosure norms apply even in academia.

**Start private, flip to public at submission / preprint:**
- **The harness and experiment code.** Private while you work (you don't want your idea visible in a public commit history before you've staked it with a preprint). Public when you post to arXiv or submit — reviewers and readers increasingly expect a code link, and it's a credibility signal. A clean public repo with a good README is, frankly, a stronger portfolio piece than the paper for industry hiring.
- **Reproduction instructions** — enough to reproduce the *headline* result from public components, without shipping the private raw data.

**Practical repo hygiene:**
- One repo per paper, or a monorepo with clear subdirs if you're disciplined. Given the shared harness, I'd do a **monorepo**: `harness/` (shared), `paper-recovery/`, `paper-toolseo/`, etc. Keep it private, make *individual result artifacts* public via a separate clean "release" repo when each paper ships.
- Never commit API keys — `.env` in `.gitignore` from commit one (your ResearchAgentAssistant README already does the `.env.example` pattern; keep it).
- Tag a release at submission (`v1.0-workshop-submission`) so the exact reviewed state is frozen.
- A `CITATION.cff` and a clear license (Apache-2.0, matching ARIA) once public.
- Write the README as if a hiring manager will read it — because one will. Your three existing READMEs are genuinely strong at this; hold that bar.

**On "should it be public at all":** yes, eventually, for the code and method. Open code is a major credibility and career asset and costs you little once the paper is out. The thing you protect is the *raw research data and unpublished analyses*, not the code. That split — open method, closed data — is standard and defensible, and you're already doing it.

---

## The one-paragraph summary

Treat these as **one research program, not five projects**: build a single reusable experiment harness, then ship focused papers off it. Do **A+B first** — it's the direct, defensible continuation of your ARIA work, and "detection is not repair, and here's the counterfactual recovery matrix" is a Q1-shaped finding. Hold **C** as your high-upside second paper (freshest, best headline, but pair the attack with a defense before open-sourcing). Use **D** as a clean third or a bonus section. **Novelty-check E** before spending a day on it. Run a two-week kill test before committing to any of them. Let Claude Code build the harness while you own the design and interpretation. Keep the repo private with raw data always private; flip the code public at preprint. Keep your README bar exactly where it already is.

---

*Next step whenever you're ready: pick the one you're committing to and I'll turn it into a formal proposal — precise RQs, a full experiment matrix with every cell specified, baseline definitions, statistical plan (how many runs for significance), threat-to-validity analysis, a week-by-week timeline against a real deadline, and a shortlist of target venues with their dates.*
