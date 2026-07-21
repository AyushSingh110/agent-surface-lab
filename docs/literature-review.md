# Literature Review — `agent-surface-lab`

*Gate 2 deliverable. Consolidated scan of recent work bearing on the two studies
(`paper-recovery` = Ideas A+B; `paper-toolseo` = Idea C). All summaries are paraphrased in my
own words. **No source text is quoted.** Everything listed is a real paper/artifact I located;
where my reading is abstract-level rather than a full read, I say so explicitly, per CLAUDE.md's
honesty rules — I would rather under-claim my depth than overstate it.*

**Read-depth key:** `[FULL]` = fetched and read the paper body/abstract page directly;
`[ABS]` = read the abstract/summary via search index and secondary pages, not the full PDF;
`[LEAD]` = referenced by another paper, **not yet read** — flagged, not characterized.

**Scan date:** 2026-07-21. This area moves fast; re-check within ~3 months before submission.

---

## Part 1 — Papers bearing on `paper-recovery` (Ideas A + B)

### Failure attribution / diagnosis (the crowded neighbourhood our work sits next to)

**1. "Which Agent Causes Task Failures and When?" — the Who&When benchmark** — arXiv:2505.00212, ICML 2025 Spotlight. `[ABS]`
- **Core claim.** Attributing a multi-agent failure to the responsible agent *and* the decisive step is a distinct, hard task, and current models are bad at it.
- **Method.** A dataset of failure logs from 127 multi-agent systems with fine-grained annotations linking each failure to a responsible agent and a decisive error step; several automated attribution methods evaluated.
- **Key numbers.** Best method ~53.5% at naming the responsible agent but only ~14.2% at pinpointing the decisive step; some methods below random; even strong reasoning models (o1, R1) are not practically usable.
- **Leaves open.** Everything *after* attribution — what to do once you know where it broke. This is precisely the gap our recovery study targets.

**2. Who&When Pro** — arXiv:2607.09996. `[ABS]`
- **Core claim / method.** A much larger attribution benchmark: ~12,326 traces across 26 source benchmarks, single- and multi-agent, multimodal, built with a warm-started error-injection pipeline that yields golden labels for responsible agent, decisive step, and failure mode.
- **Relevance.** This is a candidate *source of labeled failing traces* for our study (relevant to the pending trace-provenance decision), and it confirms the field is still investing hard in detection, not repair.

**3. "Seeing the Whole Elephant"** — arXiv:2604.22708. `[ABS]` A 2026 attribution benchmark emphasizing full-trace observability; reinforces that attribution is the saturated activity.

**4. AgenTracer** — arXiv:2509.03312. `[FULL]`
- **Core claim.** SOTA LLMs score <10% on multi-agent failure attribution; a purpose-built small model beats them.
- **Method — important for us.** Builds its training data (TracerTraj) using **counterfactual replay** (re-execute trajectories with modifications to isolate the failure source) plus programmatic fault injection, then trains an 8B model with RL. Reports up to +18.18% attribution accuracy over proprietary models and 4.8–14.2% downstream gains.
- **Crucial distinction.** It uses counterfactual replay **for attribution** (finding who/when), *not* to measure whether an intervention **recovers** the run. The method primitive overlaps ours; the research question does not. It gestures at "self-correcting systems" as downstream potential but does not measure recovery efficacy.

**5. GraphTracer** — arXiv:2510.10581. `[ABS]` Builds Information Dependency Graphs to trace root causes through data dependencies rather than time order; ~+18% attribution accuracy. Again attribution, not recovery.

**6. ErrorProbe — "Towards Self-Improving Error Diagnosis in Multi-Agent Systems"** — arXiv:2604.17658, ACL 2026 Findings (King's College London / Amazon). `[ABS]`
- **Core claim/method.** A self-improving *diagnosis* pipeline: operationalize a failure taxonomy to catch local anomalies, backward-trace to prune context, then a Strategist/Investigator/Arbiter team validates error hypotheses via tool-grounded execution.
- **Relevance.** Diagnosis + self-improvement, still upstream of "does acting on the diagnosis fix the run?" Useful as a source of a failure taxonomy to compare ours against.

**7. FlowFixer — "Diagnosis-Driven Automatic Repair for Agentic Workflow via Symbolic Inference"** — arXiv:2607.02882. `[FULL]`
- **This is the closest existing work to our repair contribution — read it carefully.**
- **Core claim.** Automatically *repairs* failing agentic workflows by diagnosing root cause and applying targeted edits, rather than generic fixes.
- **Method.** **Symbolic/static analysis**, not counterfactual replay: it turns trajectories into symbolic representations, infers behavioral specs, and checks outputs against them. It explicitly contrasts itself with intervention-and-replay causal approaches.
- **Key numbers.** ~71.3% aggregate repair success; repairs categorized by *operator* (Remove 35% / Append 22% / Replace 21% / Insert 18% / Swap 4%) and by *node type* (LLM/Agent 47%, Code/Template 20%, Knowledge 15%, Logic/Control 11%, Tool 7%). ~17K tokens/repair vs ~38K baseline; a pre-execution filter with 99.7% precision / 84.6% recall.
- **What it does NOT do (our whitespace).** No intervention-class × failure-class **recovery matrix**; **no iatrogenic rate** (never measures repairs that make a working-enough run worse); no counterfactual-replay causal verification; no cost-aware early-stopping / Pareto framing. It repairs *workflow graphs* (Dify/Coze/n8n-style), not *trajectories* measured against ground truth.

**8. DoVer** — referenced inside FlowFixer as an intervention-driven approach that repeatedly modifies and replays agent behavior to estimate causal effects. `[LEAD — NOT READ]`
- **Flag.** This is the single most important novelty check outstanding for `paper-recovery`. From the one-line reference alone it sounds methodologically close to our counterfactual-replay core. I have **not** read it and will not summarize it. **We must pull and read DoVer before committing to the recovery method framing.** Treat this as a possible partial scoop until checked.

### Does "reflect and retry" actually help? (the incumbent our study puts on trial)

**9. "Large Language Models Cannot Self-Correct Reasoning Yet"** — arXiv:2310.01798. `[ABS]` Argues intrinsic self-correction (no external feedback / oracle) does not reliably improve reasoning and can *degrade* it. This is the prior-art backbone for our H3 (reflect-and-retry is net-harmful on some classes) — it means our hypothesis is credible but also that the *general* claim "self-correction can hurt" is already on record; our contribution has to be the *per-failure-class, counterfactually-verified* breakdown, not the bare claim.

**10. "Self-Reflection in LLM Agents: Effects on Problem-Solving Performance"** — arXiv:2405.06682. `[ABS]` Finds reflection *helps* in many agent settings, strongest when initial accuracy is low. Taken with #9, the literature is genuinely split — which is exactly the opening for a counterfactual, class-conditional measurement.

**11. "Are You Sure?" (FlipFlop experiment)** — arXiv:2311.08596. `[ABS]` Challenging an LLM's answer often flips it to a wrong one — evidence that intervention can be iatrogenic. Supports our iatrogenic-rate framing.

---

## Part 2 — Papers bearing on `paper-toolseo` (Idea C)

### The setup papers (these established the premise)

**12. RAG-MCP** — arXiv:2505.03275. `[FULL]` Retrieval-augmented tool selection: index tool descriptions, retrieve the top few, only show those to the model — cuts prompt tokens >50% and roughly triples selection accuracy (43.13% vs 13.62%). **Key implication for us:** the retrieval runs *on the description text itself*, so a Tool-RAG defense is itself hijackable by description optimization — supports our planned "the existing fix doesn't help here" beat.

**13. MCPToolBench++** — arXiv:2508.07575 (Ant Group). `[ABS]` Large realistic MCP tool-use benchmark: ~1.5K queries over 40+ categories, drawn from a marketplace of 4,000+ MCP servers; metrics for planning and execution success. A candidate substrate/realism reference for our synthetic registry.

**14. "MCP Tool Descriptions Are Smelly!"** — arXiv:2602.14878 (Queen's University). `[ABS]` Audits 856 tools / 103 servers: 97.1% have at least one "description smell," 56% don't state purpose, 89% don't say when (not) to use the tool. Augmenting descriptions raises task success ~5.85 pts median but adds ~67% more steps and *regresses* 16.67% of cases. One of the two premise papers our thesis builds on.

**15. "From Docs to Descriptions: Smell-Aware Evaluation of MCP Server Descriptions"** — arXiv:2602.18914. `[ABS]` Companion line to #14: smell-aware evaluation/generation of server descriptions. Establishes that description *quality* is measurable and poor — necessary groundwork, but stops at quality, not adversarial strategy.

**16. TDQS — "Tool Definition Quality Score"** — Glama practitioner writeup (glama.ai, 2026-04-03). `[ABS — blog, not peer-reviewed]` A practitioner metric operationalizing the "97% of descriptions are defective" finding into a score. Cite as industry signal of relevance, **not** as a research baseline.

**17. "Learning to Rewrite Tool Descriptions for Reliable LLM-Agent Tool Use"** — arXiv:2602.20426. `[ABS]` Uses supervised fine-tuning to rewrite tool descriptions so agents select more reliably. Relevant as a *benign* description-optimization method — the mirror image of our adversarial optimizer, and a possible defense component (normalize toward a learned "good" description).

### The near-scoops — read these carefully, they move our novelty verdict

**18. BiasBusters — "Uncovering and Mitigating Tool Selection Bias in LLMs"** — arXiv:2510.00307, ICLR 2026 poster. `[FULL]`
- **Core claim.** Among functionally equivalent tools, LLMs are systematically biased by superficial metadata; this is a fairness/market-distortion problem.
- **Method.** 10 clusters × 5 equivalent APIs, 100 balanced queries each, 7 models; selection distributions compared via total-variation distance; three probes — attribute correlation, metadata perturbation (scramble name/description), and biased continued pre-training.
- **Key numbers.** All models biased (δ ≈ 0.3–0.4). Semantic query↔description similarity is the strongest single driver (but explains <40% variance). **Description perturbations shift selection by TV ≈ 0.3–0.45; name-only changes barely move it.** Biased pretraining pushed one endpoint from 0.6%→12.8% (~20×).
- **Defense.** Filter to a relevant subset with a small LLM, then sample uniformly — cuts combined bias 0.38→0.09 at ~0.996 precision.
- **Overlap with us.** This substantially covers our **RQ1** (capability-equivalent tools; text moves selection) and offers a **defense** (our RQ4). It is framed as *bias/fairness*, not *adversarial optimization*, and does **not** test persistence-after-failure or an active text optimizer.

**19. "Agent-Facing Information Design in LLM Tool Registries"** — arXiv:2605.23916. `[FULL]`
- **This is the strongest partial scoop of `paper-toolseo`.**
- **Core claim.** Tool registries lack accountability, so providers can win selection through marketing language rather than capability.
- **Method.** ~17,700 experiments, 5 models, 10 domains, **capability held constant**, isolating description wording.
- **Key numbers.** Subjective language (superlatives, benefit framing) accounts for essentially the *entire* optimization effect; fabricated claims add nothing beyond "legal puffery"; superlatives dominate (standardized coef ≈ +0.35); **system-prompt warnings don't work for 4 of 5 models.**
- **Defense proposed.** A structural fix: split *selection-facing* descriptions (registry-controlled) from *marketing-facing* ones (provider-authored, shown only post-selection).
- **Explicitly leaves open.** Whether agents *learn to discount* manipulative descriptions over repeated interactions — i.e., **our RQ3 (persistence after a well-described tool visibly fails).**
- **Overlap with us.** Covers much of our **RQ1 (attack effect, capability constant)** and **RQ4 (defense, incl. showing warnings fail)**. What it does *not* do: an explicit adversarial *optimizer* (our DSPy attacker) framed as an attacker; the **malicious-tool** security stinger; the persistence/learning question; Tool-RAG-is-also-hijackable.

**20. Over-privileged tool selection** — arXiv:2606.20023. `[ABS]` Adjacent: agents pick more-privileged tools than needed. A related "selection is driven by the wrong signal" result; not description-adversarial, but worth a sentence in related work.

---

## Part 3 — Gap analysis

| Our study | Our specific move | Closest existing work | What is NOT yet done (our whitespace) |
|---|---|---|---|
| **Recovery A — recovery matrix** | Counterfactual-replay recovery rate per (intervention × failure class) | AgenTracer (replay for *attribution*); FlowFixer (symbolic *repair*, aggregate rate) | No one crosses intervention × failure class as a **counterfactually-verified recovery matrix**; FlowFixer repairs workflow graphs, not replayed trajectories vs ground truth |
| **Recovery A — iatrogenic rate** | Fraction where intervening is worse than no-op, per class | "LLMs can't self-correct" (#9), FlipFlop (#11) — general | The *general* "self-correction can hurt" claim exists; the **per-failure-class iatrogenic rate measured by replay** does not |
| **Recovery A — reflect-and-retry on trial** | Test the incumbent per class | #9/#10 split literature | Nobody adjudicates the split with a **class-conditional counterfactual**; that adjudication is the contribution |
| **Recovery B — cost-aware early stopping** | Pareto: tokens saved vs correct runs killed | Attribution/prediction benches; FlowFixer's efficiency numbers | No **decision-theoretic Pareto frontier over abort thresholds** in the agent-failure setting that I found |
| **ToolSEO RQ1** | Text buys selection, capability held identical | **2605.23916; BiasBusters** | **Largely done.** Both establish this. RQ1 is no longer a novel headline. |
| **ToolSEO RQ3** | Does the hijack persist after the tool visibly fails? | 2605.23916 **explicitly lists this as open** | **Open.** This is now the live contribution. |
| **ToolSEO RQ4 defense** | Outcome/execution-based reputation vs text normalization | BiasBusters (filter+uniform); 2605.23916 (structural split); #17 (rewrite) | Partial. Text-side and structural defenses exist; **execution-outcome reputation** as the generalizing defense is under-explored |
| **ToolSEO — attack framing** | DSPy optimizer as an *adversary*; malicious-tool stinger; Tool-RAG-is-hijackable | RAG-MCP (retrieval on text); above | The **adversarial/security** framing (active optimizer + malicious tool winning routing) is still relatively open |

---

## Part 4 — Honest novelty verdict per study

**`paper-recovery` (A+B): gap is REAL but SHRINKING — move fast, and read DoVer first.**
- The attribution/diagnosis neighbourhood is saturated (Who&When, Who&When Pro, AgenTracer, GraphTracer, ErrorProbe). None of them measure **recovery efficacy** as a counterfactual, class-conditional matrix with an iatrogenic rate. FlowFixer (2607.02882) is the nearest *repair* paper but uses symbolic inference, reports only aggregate repair rate, and never measures iatrogenic harm or a Pareto — so our core is still standing.
- **Two real risks.** (1) **DoVer** — referenced as intervention-and-replay causal-effect estimation; unread; **could be a partial scoop of the method.** Pull and read before finalizing. (2) The tempo: three+ 2026-Q3 repair/diagnosis papers suggest a bigger lab could publish an adjacent recovery study while we build. Mitigate by scoping tight (the counterfactual recovery matrix + iatrogenic rate is the defensible core) and shipping the kill test fast.
- **Verdict: proceed, contingent on the DoVer check.** If DoVer already does per-class counterfactual recovery with an iatrogenic measure, we re-scope toward Idea B's cost-aware Pareto (which nobody above does) as the lead.

**`paper-toolseo` (C): the original headline is largely SCOOPED; a narrower gap remains — this needs your design call.**
- I have to say this plainly (CLAUDE.md §3): **RQ1 as originally framed — "you can buy 20+ points of selection share with description text alone, capability held identical" — is no longer novel.** BiasBusters (ICLR 2026) and especially *Agent-Facing Information Design* (2605.23916, ~17,700 experiments) have both demonstrated it, and 2605.23916 also shows prompt-warning defenses fail and proposes a structural defense. Running our kill test would likely *reproduce* their result, not establish a new one.
- **What is still genuinely open:**
  1. **RQ3 — persistence/learning:** does the hijack survive the inferior tool *visibly failing*? 2605.23916 explicitly flags this as unanswered. This is the strongest remaining contribution.
  2. **Execution-outcome reputation as a defense** that generalizes where text-normalization and structural splits don't (our H4).
  3. The **malicious-tool security stinger** (an inferior/harmful tool winning routing) and the **Tool-RAG-is-also-hijackable** result — framing beats more than novel mechanisms.
- **Verdict: the study needs a pivot, not a kill.** As written it is at high scoop risk. Re-centered on **persistence-after-failure + outcome-based reputation defense** (with the attack as reproduction/setup, not the headline), it is defensible. **This is a science/design decision and therefore yours** — I'm flagging it, not deciding it. Options are laid out in the framing notes below.

---

## Part 5 — Framing notes (how each intro should position)

**`paper-recovery` intro.** Open on the field-wide asymmetry: an enormous, still-growing effort on *attribution* (cite Who&When → Who&When Pro → AgenTracer → GraphTracer → ErrorProbe) versus near-silence on whether detection is *actionable*. Position the paper as the first to answer the on-call engineer's real question — *given a detected failure, what actually recovers the run?* — measured causally by counterfactual replay rather than an LLM judge. Distinguish from FlowFixer explicitly: we verify by replay against ground truth and we report the iatrogenic rate (repairs that backfire), which repair papers omit. Fold the split self-correction literature (#9 vs #10) in as the specific incumbent we adjudicate. Cite DoVer honestly once read.

**`paper-recovery` (Idea B) intro.** Frame strictly as **cost-aware early stopping**, never as "a failure classifier." Lead with the Pareto (tokens saved vs correct runs killed); position against the prediction/attribution benches as "they tell you *that* it fails, we tell you *when to pull the plug*." This economics-of-agents angle is where the least prior art sits.

**`paper-toolseo` intro (contingent on your pivot decision).** Do **not** claim "we show description text can buy selection" as the contribution — cite 2605.23916 and BiasBusters as having established it, and stand on their shoulders. Lead instead with the unanswered consequence: agents **don't learn** — a well-described dud keeps winning *after it visibly fails* — and with an **outcome-grounded reputation defense** that fixes what text-side and structural defenses can't. Keep the security stinger (malicious tool wins routing) as the memorable hook, and keep attack+defense shipping together (CLAUDE.md rule 6).

---

## Outstanding actions before Phase 3/4
1. **Read DoVer** (recovery method scoop check) — highest priority novelty task.
2. **Your call on the toolseo pivot** — kill / narrow-to-RQ3+defense / invert order. Design decision, yours.
3. Consider **Who&When Pro (2607.09996)** as a trace source — feeds the pending trace-provenance decision.

*All citations above correspond to real, locatable arXiv listings / pages I accessed on 2026-07-21.
Where I marked `[ABS]` or `[LEAD]`, my reading depth is limited accordingly and stated so on purpose.*

---

## Addendum (2026-07-21) — DoVer deep-read + the counterfactual-repair cluster it belongs to

*Requested before freezing the replay design. DoVer was the `[LEAD]` flagged above; reading it surfaced two more
direct neighbours (CausalFlow, Causal Agent Replay), so this addendum covers the cluster honestly, not just DoVer.
Read-depth: DoVer `[FULL]` (abstract + PDF body via fetch; some interior tables I could only read at a hedged
level — flagged inline); CausalFlow / CAR `[ABS]`.*

**DoVer — "Intervention-Driven Auto Debugging for LLM Multi-Agent Systems"** — arXiv:2512.06749 (Dec 2025).

### 1. What DoVer actually does
DoVer argues that log-only failure localization produces *untested* hypotheses and that single-step attribution is
ill-posed (several different edits can each independently fix a run). Its move: **stop guessing from passive logs;
intervene in-situ and verify by replay.** Pipeline — (a) generate candidate attribution hypotheses from the logs,
then (b) **validate each by targeted intervention + in-place replay**: preserve every step before the implicated
step, apply an edit there (message edits, plan alterations, action replacement, re-prompting, tool correction —
*several types; I could not pin an exact taxonomy count from my read*), re-run forward, and measure whether the run
now resolves or makes **milestone/utility progress**. So: **it does use counterfactual replay, like us** — not an
LLM judge, but an outcome/progress metric (softer than a deterministic ground-truth boolean). Crucially, the
abstract **frames DoVer as recovery/repair-oriented**, explicitly moving away from attribution toward "does the
intervention resolve the failure or make quantifiable progress." Headline: recovers **~49% of previously-failed
trials** in its strongest setting (GSMPlus / AG2), with further results on GAIA and AssistantBench under
Magentic-One. It is a **multi-agent** debugging system.

### 2. Direct overlap with our paper-recovery — stated plainly, not softened
- **Our core method primitive is shared.** DoVer applies an intervention at a failure step and replays forward to
  see if the outcome improves. That is exactly our replay-and-verify mechanic.
- **Our stance is partially scooped.** "Detection is not repair — you must intervene and *verify*, because a
  detected failure is not a repaired one" is essentially DoVer's opening argument. We can no longer claim the
  intervene-and-verify framing as novel; DoVer (Dec 2025), and then CausalFlow and CAR (mid-2026), already occupy
  it. Our **RQ1** (per-intervention recovery rate, measured causally) is, at the level of "measure recovery by
  replay," **already demonstrated** by DoVer.
- **Adjacent neighbours confirm the space is now crowded:** *CausalFlow* (arXiv:2605.25338) — causal attribution
  **plus minimal counterfactual repair**, turning failed runs into validated (wrong-step → corrected-step) pairs;
  *Causal Agent Replay* (arXiv:2606.08275) — structural-causal-model do-operations replayed under the same
  stochastic policy, measuring outcome-distribution shift (attribution-focused). The "counterfactual replay for
  agent failures" primitive is no longer differentiating on its own.

### 3. What DoVer (and the cluster) do NOT do — the ground we still own
- **Iatrogenic rate — not measured (our biggest differentiator).** DoVer applies interventions to already-failed
  trials and reports *gains* only. It has no no-op control on runs that might self-recover and no accounting of
  interventions that make a salvageable run *worse*. Our RQ2 / H3 (reflect-and-retry is net-harmful on
  hallucination) is squarely outside DoVer's frame. CausalFlow/CAR abstracts don't report it either.
- **Full intervention × failure-CLASS recovery matrix — not done in our sense.** DoVer appears to break results by
  broad failure modality (reasoning vs tool-use) *(this is the part of my read that was hedged — treat as
  "partial/uncertain")*, but not a systematic matrix over a principled 5-class taxonomy (ARIA's) crossed with a
  fixed intervention set. The **matrix as the object of study** remains ours.
- **Recovery decay with detection LATENESS — not studied.** Our RQ3 (catching at step 8 vs step 3) is untouched.
- **Bridge to early PREDICTION / cost-aware early stopping (our Idea B) — absent.** DoVer relates to prediction
  literature but doesn't integrate a predict→intervene→verify arc, and has no Pareto/economics framing.
- **Cleaner causal hygiene available to us.** DoVer uses (i) LLM log-summarizer localization, (ii) a milestone/
  utility progress score, (iii) a multi-agent setting. We instead use **oracle-labeled step *k*** (decouples
  detection from repair), a **deterministic per-task verifier** (harder ground truth), and a **single-agent**
  scaffold — a tighter counterfactual than DoVer's.

### 4. Design lessons for our recorder/replay schema — act on these NOW
- **Record enough to reconstruct the exact context at step *k*, not just the tool call.** DoVer preserves *all
  prior steps* and re-runs forward. Our JSONL per-step schema (turn/tool_name/tool_args/tool_result/llm_output)
  must also let us rebuild the **full running message history** up to *k* (either store it per step or make it
  deterministically reconstructable). If we only store tool calls, replay can't recreate the prompt the model
  actually saw. **→ add a per-step context/message-state field (or a reconstruct() that is tested).**
- **Decide and log a determinism policy — this is the stochastic-replay confound.** DoVer does not discuss it; CAR
  leans into it by replaying under the same stochastic policy and measuring a *distribution*. We must choose: (a)
  fix seed + temperature=0 for a deterministic single-sample counterfactual (clean, cheap, but ignores variance),
  or (b) sample **N** replays per (intervention, trace) and report a recovery-rate *distribution* (honest about
  stochasticity, more compute). I lean (b) at least N≥3 so a single lucky/unlucky sample can't masquerade as a
  recovery — but this is the **statistical-plan decision (§8 item 10) and is the human's.** Either way, the
  recorder/replay must log seed, temperature, and model tag on every replay.
- **Keep ground truth strictly deterministic (already decided) — it is a genuine methodological edge over DoVer's
  milestone/utility score.** Don't let a progress-heuristic leak into the recovery metric.
- **Keep detection and repair decoupled via oracle *k* (already decided) — another edge over DoVer's LLM
  localization.** Preserve this separation in the kill test.

### 5. Verdict
**Proceed with a sharpened framing — do NOT pivot away from recovery, and do NOT keep the old headline.** The bare
"measure recovery by counterfactual replay / detection-is-not-repair" claim is now occupied by DoVer, CausalFlow,
and CAR. Our defensible, still-open contribution is the **class-conditional, iatrogenic-aware recovery
*accounting*** — the (intervention × failure-class) matrix, the **iatrogenic rate** (interventions that backfire,
reflect-and-retry chief among them), the **lateness-decay** curve, and the **bridge to cost-aware early prediction
(Idea B)** — all under tighter causal hygiene (oracle *k*, deterministic ground truth, single-agent). Reframe the
intro from "you should intervene, not just detect" (DoVer said it) to **"not all intervention helps — here is which
repair works on which failure, and where standard self-correction actively harms."** Cite DoVer/CausalFlow/CAR as
the counterfactual-repair foundation we build the accounting on top of.
