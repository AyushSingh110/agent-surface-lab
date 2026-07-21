# CLAUDE.md — Operating Manual for `agent-surface-lab`

This file tells you (Claude) how to work in this repository. Read it fully before acting. If anything you're about to do conflicts with it, stop and ask.

---

## 1. What this repo is

This is a **research monorepo** for a program of empirical studies on LLM-agent behavior. The unifying thesis across every study is:

> **LLM agents act on surface text and surface cues rather than the deeper property those cues are supposed to represent.**

Concretely, the planned papers are:

- **`paper-recovery/`** (Ideas A + B) — *Detection is not repair.* Predict agent failure early, intervene, and measure via counterfactual replay whether the intervention actually recovers the run. Produces a recovery matrix (intervention × failure class) and a cost-aware early-stopping Pareto analysis.
- **`paper-toolseo/`** (Idea C) — *Tool descriptions as an adversarial surface.* Measure how much tool-selection share can be bought by optimizing description text alone (capability held identical), then propose and evaluate defenses.

Full context lives in `docs/individual-research-plan.md`. **Read that file before starting work on any paper.** It contains the research questions, hypotheses, baselines, and metrics for each study.

---

## 2. Division of labor — this is critical

- **You (Claude) own the engineering.** The harness, trace recorder, replay layer, tool sandbox, metrics, plotting, the DSPy attacker for the toolseo paper, tests, and glue code. Build these well.
- **The human owns the science.** Experimental design, hypotheses, choice of baselines, and interpretation of results are theirs. You may *suggest* design improvements, but you do **not** silently change an experimental design, a baseline, or a metric. If you think a design is flawed, say so and wait.

You can implement a flawed experiment perfectly. That helps no one. When a task touches experimental validity (what counts as a fair baseline, whether a confound is controlled, whether a result supports a claim), **flag it and ask rather than proceeding.**

---

## 3. Absolute rules — never violate

1. **Never fabricate, hardcode, or "helpfully" fill in results.** If an experiment hasn't run, its numbers do not exist. No placeholder metrics that look real. No synthetic "expected" outputs presented as measured.
2. **Never invent data.** If a dataset or trace is missing, say so. Do not generate fake traces and pass them off as real.
3. **Report failures honestly.** If a result is null, weak, or contradicts the hypothesis, report it plainly. A null result is a finding, not something to paper over. The whole point of this line of work is honest measurement.
4. **Never commit secrets.** `.env` is gitignored from commit one. No API keys, tokens, or credentials in code, logs, or commit messages ever.
5. **Never commit raw research data.** Raw traces, labeled datasets, and full analyses stay local and gitignored (`data/`, `*.jsonl`). Only aggregate results and method code are tracked.
6. **For the toolseo paper: never open-source a working attack without its paired defense.** Attack and defense ship together.

---

## 4. Code standards — production quality

Write code as if a senior engineer will review it and a stranger will reproduce it.

- **Language:** Python 3.10+. Type hints on every function signature. No untyped public functions.
- **Structure:** small, single-responsibility functions; pure functions where possible; dependency-inject anything stateful (models, stores) so experiments are testable and swappable.
- **Comments — the standard the human asked for:** comment the **why**, never the **what**. No comments that restate the code (`# increment i`). Where a decision is non-obvious (a threshold choice, a workaround, a subtle correctness reason), write a **detailed** comment explaining the reasoning. Every public function gets a docstring stating purpose, args, returns, and any important assumptions. The rule of thumb: if a comment would still make sense after the code changed, it's a good comment; if it just narrates the current line, delete it.
- **No dead code, no commented-out blocks left behind, no unused imports.**
- **Errors:** fail loudly and early with clear messages. No silent excepts that swallow failures — in research code, a swallowed error is a corrupted result.
- **Reproducibility:** every experiment run must set and log its random seed, its config, the local Ollama model/backend used (name and tag), and a timestamp. Prefer config files (YAML/dataclass) over hardcoded constants scattered in code.
- **Tests:** the harness (recorder, replay, metrics) gets `pytest` tests. Experiment scripts don't need full coverage, but any non-trivial metric computation does — a wrong metric silently invalidates a paper.
- **Determinism:** replay and metric code must be deterministic given the same inputs. Flag any nondeterminism.

---

## 5. The two documents you maintain

### `LOGBOOK.md` — the running record (update continuously)

This is the single source of truth for *what has been executed and why*. **After every meaningful action** (building a component, running an experiment, getting a result, hitting a wall, making a design decision), append a dated entry. Format:

```
## YYYY-MM-DD — <short title>
**What:** what was built or run.
**Why:** the reason / which RQ or hypothesis it serves.
**Config:** seed, model/backend, key parameters (or link to the config file).
**Result:** what actually happened — numbers, or the observed behavior. Honest, including nulls.
**Next:** the immediate next step or open question.
```

Never overwrite past entries; only append. This log is what makes the work reproducible and is the raw material for the paper's intro and method sections. Treat it as sacred.

### `README.md` — the public face (update only on milestones)

Update the README **only when something is genuinely achieved** — a working harness, a completed experiment with a real result, a shipped paper. Do not update it with aspirational or in-progress claims. When you do update it, match the quality bar of the human's prior work: clear one-line pitch, honest status badges, aggregate results only (never raw data), and a clean quick-start. If a claim isn't backed by a logged, reproduced result, it does not go in the README.

---

## 6. Working discipline

- **Kill test first.** For any new study, the first thing to build is the cheapest experiment that could *disprove* the central hypothesis — not the full harness. Confirm the effect exists before investing in infrastructure. The research plan specifies each study's kill test.
- **Headline figure early.** Once real data exists, build the paper's headline figure (recovery matrix / Pareto curve / hijack-rate plot) before polishing anything else. Let it tell you whether the story holds.
- **One backbone, one scaffold.** Pin one local Ollama model and one agent scaffold. Do not expand this without the human explicitly asking. Scope creep kills research projects.
- **Small commits, clear messages.** Each commit does one thing. Commit messages state what changed and why, in the imperative ("add replay layer", not "added stuff").
- **Ask before large or irreversible moves:** restructuring directories, changing a metric definition, deleting anything, adding a heavy dependency, or anything that would alter an already-collected result.

---

## 7. Environment

- Config in `.env` (gitignored); template in `.env.example`. No hosted-API secrets are needed — the backbone is local.
- A single local Ollama backbone drives everything (host URL + model name/tag configured via `.env`). No Groq, no hosted APIs.
- Pin dependencies in `pyproject.toml` / `requirements.txt`. Flag any new dependency before adding it.

---

## 8. When in doubt

Prefer the honest, smaller, verifiable thing over the impressive, larger, unverified thing. This is a research repo: correctness and reproducibility beat features and polish every time. If you're unsure whether something affects the validity of a result, assume it does and ask.
