# Setup — `agent-surface-lab` (Ollama-only)

**Your environment (confirmed 2026-07-21):** Windows 11, 16 GB RAM, 4 GB VRAM,
Intel i7-12700H, ~477 GB free. Commands below are written for **Windows Command
Prompt (`cmd.exe`)**. Where a step needs PowerShell instead, it is labelled
**[PowerShell]**.

**Pinned backbone (per work-plan §8 item 8):**
- **Default: `llama3.1:8b`** — native tool-calling, same family as ARIA (~4.7 GB download).
- **Lighter fallback: `llama3.2:3b`** — if the 8B is too slow or memory-tight (~2 GB).

On your hardware the 8B model partially offloads to the 4 GB GPU and runs the
remainder on the CPU — expect usable-but-not-instant throughput. If iteration
feels slow, switch `OLLAMA_MODEL` to `llama3.2:3b` in `.env`.

---

## LIST A — COMMANDS YOU RUN MANUALLY

*You run these; I cannot (they install software, start a server, download models,
or create your git history). Run them in order. Each line notes what it does and
the output that confirms success.*

### A1. Install Ollama
1. Download the Windows installer: open **https://ollama.com/download** and get
   `OllamaSetup.exe` (or direct: **https://ollama.com/download/OllamaSetup.exe**).
2. Run `OllamaSetup.exe` and click through. It installs Ollama **and starts a
   background server** automatically on `http://localhost:11434`.
3. Confirm the CLI is installed (new `cmd` window):

   ```
   ollama --version
   ```
   *Does:* prints the installed version. *Expected:* something like
   `ollama version is 0.x.x`. If `cmd` says it's not recognized, close and reopen
   the terminal (PATH needs to refresh), or reboot.

### A2. Confirm the Ollama server is running
```
curl http://localhost:11434/api/tags
```
*Does:* asks the local server for its installed models. *Expected:* a JSON
response (e.g. `{"models":[...]}`) — an empty list is fine before you pull.
If it errors with a connection refused, start the server manually (see A5).

### A3. Pull the model
```
ollama pull llama3.1:8b
```
*Does:* downloads the default backbone (~4.7 GB — one-time). *Expected:* a
progress bar ending in `success`. *(Lighter fallback, optional:
`ollama pull llama3.2:3b`.)*

### A4. Verify the model responds
```
ollama run llama3.1:8b "Reply with exactly the word: OK"
```
*Does:* runs a single prompt through the model. *Expected:* it prints `OK`
(possibly with minor extra text). Type `/bye` to exit if it stays interactive.
First response may be slow while the model loads into memory.

### A5. (Only if A2 failed) Start the server manually
```
ollama serve
```
*Does:* starts the Ollama server in the foreground. *Expected:* log lines and
`Listening on 127.0.0.1:11434`. Leave this window open and use a second `cmd`
window for other commands. (Normally the installer's background service makes
this unnecessary.)

### A6. Create and activate the conda environment
This project uses **conda** (not venv). Create and activate the `surface` env:
```
conda create -n surface python=3.11 -y
conda activate surface
```
*Does:* creates an isolated conda env named `surface` on Python 3.11 (lives
outside the repo, so nothing to gitignore) and activates it. *Expected:* your
prompt is now prefixed with `(surface)`.

Then verify you are actually in that env before anything gets installed into it:
```
python --version
conda env list
where python
```
*Expected:* `python --version` shows `Python 3.11.x`; `conda env list` shows the
`*` marker on the `surface` row; `where python` lists a path under
`...\anaconda3\envs\surface\` (NOT `base`, NOT a `.venv`).

### A7. Create your local `.env` from the template
```
copy .env.example .env
```
*Does:* creates your gitignored `.env`. *Expected:* `1 file(s) copied.` No edits
needed unless you switch to the fallback model.

### A8. Initialize git and make the first commit *(only if not already a repo)*
This repo is **already** a git repository, so you likely only need the first
commit of the new scaffolding. From the project folder:
```
git status
git add CLAUDE.md .gitignore .env.example pyproject.toml docs LOGBOOK.md
git commit -m "add operating manual, plan docs, and Ollama-only setup scaffolding"
```
*Does:* stages the tracked project files (NOT `.env`, NOT `data/`, NOT `.venv/` —
those are gitignored) and records the first commit. *Expected:* a commit summary
listing the added files. Verify nothing secret slipped in:
```
git status --ignored
```
*Expected:* `.env`, `.venv/`, and any `data/` appear under **Ignored files**.

---

## LIST B — COMMANDS I RUN MYSELF

*After you confirm LIST A worked, I run these during the build. Listed here for
transparency; you do not need to run them.*

- **B1. Install the pinned dependencies** into the `surface` conda env
  (targeted explicitly, not by relying on activation):
  `conda run -n surface pip install -e ".[dev]"`
  (installs `ollama`, `pyyaml`, `python-dotenv`, and `pytest` — see
  `pyproject.toml`; every dependency is flagged there.) I verify the env prefix
  points at `surface` **before** this runs.
- **B2. Lock exact versions** after first install for reproducibility:
  `pip freeze > requirements.txt`
- **B3. Tool-calling smoke test** — a short Python script that sends a
  one-tool request to `llama3.1:8b` via the Ollama client and checks the model
  returns a well-formed tool call. This confirms the backbone is agentic-tool
  capable before I build the runner. (I write and run this only after your A-list
  confirmation.)
- **B4. Scaffold the repo** (`harness/`, `paper-recovery/`, `tests/`, config) and
  build the minimal Recovery kill-test harness (Phase 4) — **only after Gate 3**.
- **B5. Run the pytest suite** for the recorder, replay layer, and metrics module.

---

## What I will NOT do without you
- I will not install Ollama, pull models, or start the server (LIST A is yours).
- I will not write any runner/recorder code until you confirm A4 (the model
  responds) — per your instruction.
- I will not add any dependency beyond those flagged in `pyproject.toml` without
  asking first (CLAUDE.md 6).
