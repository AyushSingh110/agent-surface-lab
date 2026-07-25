<div align="center">

# agent-surface-lab

**Do LLM agents act on the *surface text* of a cue, or on the deeper property it is supposed to represent?**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![tests](https://img.shields.io/badge/tests-82%20passing-brightgreen.svg)](tests/)
[![status: active research](https://img.shields.io/badge/status-active%20research-orange.svg)](#status)
[![backbone: local Ollama](https://img.shields.io/badge/backbone-local%20Ollama-lightgrey.svg)](docs/setup.md)

</div>

---

## What is this project?

`agent-surface-lab` is a research monorepo for a program of empirical studies on LLM-agent behavior. Every
study tests one thesis:

> **LLM agents act on surface text and surface cues rather than the deeper property those cues are supposed
> to represent** — a tool's *description* instead of its capability, the *word* "delete" instead of the
> consequence, a *detected* failure instead of a *recoverable* one, the *wording* of a repair instead of its
> intent.

The work is built on one **shared, reusable harness** (an instrumented tool sandbox, a per-step trace
recorder, a counterfactual **replay** layer, swappable interventions, deterministic metrics, and
adversarially-audited deterministic verifiers) so each study is cheap to run and reproducible. Everything
runs on a single **local Ollama** backbone — no hosted APIs.

Two studies sit on that harness:

- **`paper-recovery/` — *Detection is not repair.*** Given a failure detected at step *k*, which
  intervention actually *recovers* the run, and where does standard self-correction make it *worse*? Recovery
  is measured **causally, by counterfactual replay against a no-op control** — never by an LLM judge.
- **`paper-toolseo/` — *Tool descriptions as an adversarial surface.*** How much tool-selection share can be
  bought by optimizing description text alone, with capability held identical — and what defends against it?
  *(Second study; scoped, not yet built.)*

## What we are doing right now

Active work is on **`paper-recovery`**. In short: generate agent runs that fail, rewind each failing run to
the failure step, apply a repair intervention, replay forward, and check the *actual* outcome against
deterministic ground truth — then see which repairs help, which do nothing, and which actively harm.

## Status

**Built and tested** (`82` passing tests):

- The shared harness — trace recorder (JSONL), replay + exact-context `reconstruct`, interventions
  (`no_op` control, `reflect_and_retry`, `rollback_n`, `restart_clean`, requirement injection), deterministic
  metrics (recovery distribution, paired iatrogenic rate), and deterministic verifiers.
- A **standing adversarial audit** of every verifier (a committed battery of correct + wrong near-miss cases),
  because a mis-scored "failure" silently corrupts every downstream number — false positives are treated as
  the dangerous direction.
- Two induction task families with an orthogonal design (task shape × trigger depth × surface form).

**Early, directional observations** (small-*n* kill tests on one local model — **not** established results;
all raw data stays local):

- A capable instruction-tuned small agent rarely loops, skips deliverables, or misuses *erroring* tools. It
  fails in two reproducible ways: **hallucination-by-skipped-lookup** (inventing a fact that was available
  but unfetched) and **surface-form tool misuse** (feeding an input to a general tool when its *surface form*
  mimics the operand — e.g. `YYYYMMDD` dates or `HHMM` times fed to subtraction — while converting correctly
  when the form is structurally marked, e.g. `HH:MM`).
- **Repair wording matters:** an *imperative* repair instruction ("report the name") can recover a failure
  *less* often than doing nothing, while a *declarative* one ("the answer must be the name") recovers fully —
  the same surface-cue thesis, now on the repair itself.

These findings have been openly **retracted or corrected** where follow-up checks demanded it; that history
is kept in `LOGBOOK.md` and `docs/RESEARCH-NARRATIVE.md` rather than hidden.

## Methodology commitments

- **Causal, not judged.** Recovery is measured by counterfactual replay against a no-op control, never an LLM judge.
- **Deterministic, audited ground truth.** Every verifier is a deterministic function, adversarially audited;
  numeric answers are token- and unit-aware so "right number, wrong unit" cannot pass.
- **Honest by construction.** Null and negative results are reported plainly. Numbers below real *n* are
  labeled directional. Corrections and retractions are logged, not buried.
- **Data hygiene.** Only method and aggregate results are tracked; raw traces, labeled datasets, and full
  analyses stay local (gitignored).

## Repository layout

```
harness/            reusable core: recorder, replay, interventions, metrics, verifiers, backend
recovery_sandbox/   deterministic tools, fixtures, and task families for paper-recovery
paper-recovery/     study code: config, generation + recovery drivers
tests/              pytest suite (harness + verifier audit + sandbox)
docs/               work plan, literature review, setup, research narrative, kill-test memos
```

## Quick start

Full, OS-specific instructions are in [`docs/setup.md`](docs/setup.md). In brief:

```bash
# 1. install & start Ollama, then pull the pinned model
ollama pull qwen2.5:7b

# 2. create the environment and install (conda shown; venv also fine)
conda create -n surface python=3.11 -y && conda activate surface
pip install -e ".[dev]"

# 3. run the tests
pytest -q
```

## Documentation

- [`docs/work-plan.md`](docs/work-plan.md) — studies, research questions, and design decisions.
- [`docs/literature-review.md`](docs/literature-review.md) — related work and an honest novelty verdict.
- [`docs/RESEARCH-NARRATIVE.md`](docs/RESEARCH-NARRATIVE.md) — the project explained end-to-end, including the
  decisions and the corrections.
- `LOGBOOK.md` — the append-only, dated record of everything run.

## License

Licensed under the **Apache License 2.0** — see [`LICENSE`](LICENSE).
