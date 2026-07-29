# Setup

This project runs local LLM-agent experiments through Ollama. No hosted API is
required.

## Requirements

- Python 3.10+
- Ollama running locally at `http://localhost:11434`
- A local model pulled in Ollama, such as `qwen2.5:7b`

## Install

Create and activate an environment, then install the package with development
dependencies:

```bash
pip install -e ".[dev]"
```

Copy the environment template:

```bash
copy .env.example .env
```

On macOS or Linux:

```bash
cp .env.example .env
```

Edit `.env` if you want to use a different Ollama host or model.

## Check Ollama

Confirm the server is running:

```bash
curl http://localhost:11434/api/tags
```

Pull the default model if needed:

```bash
ollama pull qwen2.5:7b
```

## Run Tests

```bash
pytest -q
```

## Data Hygiene

Raw traces, labeled datasets, local analysis files, draft paper files, and
private planning notes are intentionally ignored by Git. The public repository is
meant to contain the reusable harness, sandbox code, tests, configuration, and
setup notes.
