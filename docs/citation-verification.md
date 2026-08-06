# Citation Verification — Phase 0.1

*Every arXiv ID appearing in `paper/main.tex` and `docs/literature-review.md`, checked against the live
arXiv listing on **2026-08-06**. Verification method: fetch `arxiv.org/abs/<id>`, compare the resolved
title / author list / abstract against how the ID is cited in this repo.*

**Headline: all 21 IDs resolve. No fabricated citations.** Three classes of real defect were found and are
recorded below: four wrong titles in the paper bibliography (fixed), one **withdrawn** paper still cited as
valid (must be removed), and several citations that were missing author lists (fixed).

---

## 1. `paper/main.tex` bibliography (11 IDs) — all resolve

| Key | ID | Resolves | Title as cited before check | Verdict |
|---|---|---|---|---|
| `whowhen` | 2505.00212 | ✅ | "Which Agent Causes Task Failures and When? (Who&When benchmark)" | OK — subtitle was truncated; **completed + authors added** |
| `agentracer` | 2509.03312 | ✅ | "AgenTracer: Failure Attribution for Multi-Agent Systems via Counterfactual Replay" | ❌ **WRONG TITLE** — real title is "AgenTracer: Who Is Inducing Failure in the LLM Agentic Systems?" **FIXED** |
| `dover` | 2512.06749 | ✅ | "DoVer: Intervention-Driven Auto Debugging for LLM Multi-Agent Systems" | ✅ exact match; **authors added** |
| `causalflow` | 2605.25338 | ✅ | "CausalFlow: Causal Attribution and **Minimal** Counterfactual Repair for **Agent** Failures" | ❌ **WRONG TITLE** — real: "…Causal Attribution and Counterfactual Repair for **LLM Agent** Failures" (no "Minimal"). **FIXED** |
| `car` | 2606.08275 | ✅ | "Causal Agent Replay: **Structural-Causal Do-Operations for Agent Failure Attribution**" | ❌ **WRONG SUBTITLE** — real: "Causal Agent Replay: **Counterfactual Attribution for LLM-Agent Failures**". **FIXED** |
| `flowfixer` | 2607.02882 | ✅ | "**FlowFixer:** Diagnosis-Driven Automatic Repair for Agentic **Workflows** via Symbolic Inference" | ❌ **WRONG TITLE** — "FlowFixer" is the system name, not part of the title; real title is "Diagnosis-Driven Automatic Repair for Agentic **Workflow** via Symbolic Inference". **FIXED** |
| `selfcorrect` | 2310.01798 | ✅ | "Huang et al. Large Language Models Cannot Self-Correct Reasoning Yet" | ✅ exact match |
| `selfreflect` | 2405.06682 | ✅ | "Renze and Guven. Self-Reflection in LLM Agents…" | ✅ exact match |
| `flipflop` | 2311.08596 | ✅ | "Are You Sure? Challenging LLMs Leads to Performance Drops (the FlipFlop experiment)" | ⚠️ real title ends "…**in The FlipFlop Experiment**". **FIXED** + authors added |
| `qwen` | 2412.15115 | ✅ | "Qwen2.5 Technical Report" | ✅ exact match |
| `mistral` | 2310.06825 | ✅ | "Jiang et al. Mistral 7B" | ✅ exact match |

### Claims made about these papers — spot-checked against abstracts

The Related Work section's substantive claims were checked, not just the titles:

- **DoVer recovers ~49% of failed trials** — ✅ confirmed verbatim in the abstract ("recovering 49% of failed
  trials" on GSMPlus/AG2; 18–28% flipped on Magentic-One/GAIA/AssistantBench).
- **FlowFixer reports ~71.3% aggregate repair rate via symbolic inference** — ✅ confirmed verbatim.
- **"The counterfactual-repair cluster does not report an iatrogenic rate"** — ✅ no abstract in the cluster
  mentions a no-op control or an iatrogenic/harm rate. The claim stands as written.
- ⚠️ **Note for our own method:** Causal Agent Replay's abstract advertises "confidence intervals for all
  reported effects." A neighbouring paper already reports uncertainty; our point estimates without CIs are a
  visible gap by comparison. This directly motivates Phase 1.

---

## 2. `docs/literature-review.md` — additional IDs (10 more) — all resolve

| ID | Resolved title | Status |
|---|---|---|
| 2510.00307 | BiasBusters: Uncovering and Mitigating Tool Selection Bias in Large Language Models | ✅ |
| 2605.23916 | Agent-Facing Information Design in LLM Tool Registries | ✅ (author: Haochuan Kevin Wang; 17,700+ trials confirmed) |
| 2505.03275 | RAG-MCP: Mitigating Prompt Bloat in LLM Tool Selection via Retrieval-Augmented Generation | ✅ |
| 2508.07575 | MCPToolBench++: A Large Scale AI Agent MCP Tool Use Benchmark | ✅ |
| **2510.10581** | **GraphTracer: Graph-Guided Failure Tracing in LLM Agents…** | 🔴 **WITHDRAWN — see §3** |
| 2602.14878 | MCP Tool Descriptions Are Smelly! … Augmented MCP Tool Descriptions | ✅ |
| 2602.18914 | From Docs to Descriptions: Smell-Aware Evaluation of MCP Server Descriptions | ✅ |
| 2602.20426 | Learning to Rewrite Tool Descriptions for Reliable LLM-Agent Tool Use | ✅ |
| 2604.17658 | Towards Self-Improving Error Diagnosis in Multi-Agent Systems | ✅ (ACL 2026 Findings) |
| 2604.22708 | Seeing the Whole Elephant: A Benchmark for Failure Attribution in LLM-based Multi-Agent Systems | ✅ (ACL 2026) |
| 2606.20023 | When Lower Privileges Suffice: Investigating Over-Privileged Tool Selection in LLM Agents | ✅ |
| 2607.09996 | Who&When Pro: Can LLMs Really Attribute Failures in AI Agents? | ✅ |

---

## 3. 🔴 GraphTracer (arXiv:2510.10581) is WITHDRAWN

**The submission was withdrawn by its own authors on 2025-12-22, citing "a fundamental error in the
methodology" that affected the validity of the main results.**

It is **not** in `paper/main.tex` — the manuscript is safe as it stands. But it is currently cited as valid
supporting evidence in three internal docs, and `docs/paper-outline.md` §2 explicitly plans to cite it in the
Related Work prose:

| File | Line | Use |
|---|---|---|
| `docs/literature-review.md` | 38 | Source #5, summarized as a valid attribution result (~+18% accuracy) |
| `docs/literature-review.md` | 120, 136 | Named in the "attribution neighbourhood is saturated" list |
| `docs/paper-outline.md` | 46 | Listed for citation in Related Work |
| `docs/RESEARCH-NARRATIVE.md` | 38 | Named in the attribution-saturation framing |

**Required action:** do not cite it as a result. The "attribution is saturated" argument does **not** depend
on it — Who&When, Who&When Pro, AgenTracer, Seeing the Whole Elephant, and Towards Self-Improving Error
Diagnosis all carry that claim independently, and all five verify clean. Drop GraphTracer from the citation
list, or mention it only as a withdrawn submission if the withdrawal itself is being discussed.

*(A withdrawn-paper citation is the kind of thing a reviewer catches and treats as a signal about the rest of
the bibliography, so it is worth removing everywhere rather than only in the manuscript.)*

---

## 4. What was changed in `paper/main.tex`

- Four bibliography titles corrected (`agentracer`, `causalflow`, `car`, `flowfixer`).
- One title completed (`flipflop`), one subtitle completed (`whowhen`).
- Author lists added to the six entries that had none (`whowhen`, `agentracer`, `dover`, `causalflow`, `car`,
  `flowfixer`, `flipflop`).
- No claim in the Related Work prose required a change — the substantive characterizations were accurate.

## 5. Standing rule going forward

Any new citation added to this project gets checked against the live listing **before** it enters a doc, and
gets a row in this table. The check is cheap; a fabricated or withdrawn citation in a published preprint is
not recoverable.
