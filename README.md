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

`agent-surface-lab` is a research repo for empirical studies on LLM-agent behavior. The work tests one
thesis:

> **LLM agents act on surface text and surface cues rather than the deeper property those cues are supposed
> to represent** — the fact that a tool call *returned without an error* instead of whether the result is
> meaningful, a *detected* failure instead of a *recoverable* one, the *wording* of a repair instead of its
> intent.

Everything is built on one **shared, reusable harness** — an instrumented tool sandbox, a per-step trace
recorder, a counterfactual **replay** layer, swappable interventions, deterministic metrics, and
adversarially-audited deterministic verifiers — so each study is cheap to run and reproducible. It all runs
on a single **local Ollama** backbone; no hosted APIs.

The active study is **`paper-recovery/` — *Detection is not repair.*** Given a failure detected at step *k*,
which intervention actually *recovers* the run, and where does standard self-correction leave it unchanged or
make it *worse*? Recovery is measured **causally, by counterfactual replay against a no-op control** — never
by an LLM judge.

## How it works

Generate agent runs that fail, rewind each failing run to its failure step, apply one repair intervention,
replay forward, and check the *actual* outcome against deterministic ground truth — then see which repairs
help, which do nothing, and which actively harm (measured against a no-op control, so a repair that hurts a
self-recoverable run is visible).

## Status

**Built and tested** (`82` passing tests):

- The shared harness — trace recorder (JSONL), replay + exact-context `reconstruct`, interventions
  (`no_op` control, `reflect_and_retry`, `rollback_n`, `restart_clean`, requirement injection), deterministic
  metrics (recovery distribution, paired iatrogenic rate), and deterministic verifiers.
- A **standing adversarial audit** of every verifier (a committed battery of correct + wrong near-miss cases),
  because a mis-scored "failure" silently corrupts every downstream number — a false *pass* is treated as the
  dangerous, silent direction.
- Two induction task families with an orthogonal design (task shape × trigger depth × surface form).

**Early, directional findings** — one primary local model (`qwen2.5:7b`), small-to-moderate *n*; treated as
directional, not settled results. Raw data stays local.

- A capable instruction-tuned small agent rarely loops, skips deliverables, or misuses *erroring* tools. It
  fails in two reproducible ways: **skipped-lookup hallucination** (inventing a fact that was available but
  never fetched) and **tool-false-validation misuse** (feeding an operand-shaped string — a `YYYYMMDD` date, an
  `HHMM` time — to a general arithmetic tool, which returns a non-error result and so *falsely validates* a
  meaningless computation).
- **What recovers skipped-lookup is *action-licensing*, not grammatical mood.** Two repair prompts that are
  grammatically identical and differ only in whether they *permit a fresh tool lookup* recover very
  differently (≈1.00 vs ≈0.16 at chain depth 1, N=10). Repairs that license the corrective action recover;
  restating the requirement without licensing it does not. *(This corrects an earlier "declarative beats
  imperative" reading, which fuller data refuted.)*
- **Tool-false-validation misuse resists every text-level repair we tried** (≤0.14, N=10): once a tool has
  "confirmed" a well-formed wrong number, prompting the model to review or restate does not remove the false
  validation — the corrupting signal is a tool result, not a prompt.
- **Recovery decays with detection lateness** — the deeper in the chain a skip is caught, the less a repair
  recovers.
- A second backbone (`mistral:7b`) reproduces the skipped-lookup *mechanism* cross-model, but is too
  unreliable at emitting tool calls to test recovery — which is itself a finding: **cross-model recovery
  evaluation is confounded by tool-calling competence.**

These findings have been openly **corrected where follow-up checks demanded it** rather than smoothed over.
See the limitations below.

## Limitations

- **Single primary model.** All recovery numbers are on `qwen2.5:7b`; the second-backbone check confirmed the
  mechanism cross-model but could not test recovery (tool-capability confound). Recovery findings are shown on
  one model, not yet model-general.
- **Synthetic sandbox.** Deterministic, small tasks and fixtures — a clean counterfactual, but external
  validity to real workloads is not established.
- **Directional *n*.** Headline extremes are firm at N=10; some cells remain N=3 and a few mid-range rates
  sit near a decision boundary. Deep-chain and dotted-version sub-families rest on small *n* and are trends,
  not point estimates.
- **Labeling.** Failure-class labels are from a single (assisted) labeler, spot-check-validated; no
  inter-annotator agreement was computed at this scale.

## Methodology commitments

- **Causal, not judged.** Recovery is measured by counterfactual replay against a no-op control, never an LLM judge.
- **Deterministic, audited ground truth.** Every verifier is a deterministic function, adversarially audited;
  numeric answers are token- and unit-aware so "right number, wrong unit" cannot pass.
- **Honest by construction.** Null and negative results are reported plainly. Numbers below real *n* are
  labeled directional. Corrections and retractions are made openly, not buried.
- **Data hygiene.** Only method code and aggregate results are tracked; raw traces, labeled datasets, and full
  analyses stay local (gitignored).

## Repository layout

```
harness/            reusable core: recorder, replay, interventions, metrics, verifiers, backend
recovery_sandbox/   deterministic tools, fixtures, and task families for paper-recovery
paper-recovery/     study code: config, generation + recovery drivers
tests/              pytest suite (harness + verifier audit + sandbox)
docs/setup.md       setup and reproduction notes
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

## License

Licensed under the **Apache License 2.0** — see [`LICENSE`](LICENSE).
