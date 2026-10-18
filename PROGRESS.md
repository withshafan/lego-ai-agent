# LEGO AI Agent — Progress

- **Current stage:** Stage 6 — Terminal chat with the local model
- **Current step:** 6.4 — Sync and run the terminal chat client
- **Completed:**
  - Stage 1.1 — Checked Python availability; Python 3.14.3 was initially the only standard per-user installation found.
  - Stage 1.2 — Searched the Windows package catalog and confirmed `Python.Python.3.12` version 3.12.10.
  - Stage 1.3 — Installed Python 3.12.10 and verified it alongside Python 3.14.3.
  - Stage 1.4 — Verified Git is installed: version 2.54.0.windows.1.
  - Stage 1.5 — Confirmed the Windows package catalog lists `Ollama.Ollama` version 0.40.5.
  - Stage 1.6 — User confirmed Ollama installation and winget package verification.
  - Stage 1.7 — Verified the Ollama executable runs directly and reports version 0.40.5.
  - Stage 2.1 — Created `D:\pyProjects\ollama\models`; current-session and persistent user `OLLAMA_MODELS` values verified.
  - Stage 2.2 — Started Ollama; an empty model list was returned before pulling the model.
  - Stage 2.3 — User verified the official Ollama library lists `llama3.2:3b` (2.0 GB).
  - Stage 2.4 — Started Ollama in the foreground; logs confirmed it listens on `127.0.0.1:11434` with the configured model folder.
  - Stage 2.5 — Pull command reported success; server logs showed HTTP 200 for `/api/pull`.
  - Stage 2.6 — Tested the model in PowerShell; it returned the exact LEGO AI Agent self-introduction.
  - Stage 3.1 — Located Python 3.12.10 at the user's Python312 installation path.
  - Stage 3.2 — Created `.venv` in the project root and verified it runs Python 3.12.10.
  - Stage 3.3 — Added and verified `.gitignore` rules for virtual environments, secrets, local data/logs, databases, model downloads, caches, editor files, Flutter output, and Node dependencies.
  - Stage 3.4 — Added `requirements.txt` with FastAPI, Uvicorn, HTTPX, Pydantic v2, pydantic-settings, pytest, and pytest-asyncio.
  - Stage 3.5 — Pushed setup files to `origin/arena/468202c8-lego-ai-agent`; user fetched and switched the Windows checkout to that branch and verified `requirements.txt`.
  - Stage 3.6 — Installed requirements in `.venv`; verified package imports and Pydantic 2.14.1.
  - Stage 5.1 — Started Ollama after quitting the tray app; logs showed the configured model folder, seven blobs, and localhost listener.
  - Stage 5.2 — Async HTTPX request to `/api/tags` returned `llama3.2:3b` and its model details.
  - Stage 6.1 — Verified `lego.APP_NAME` and `lego.__version__` from the Python 3.12 virtual environment.
  - Stage 6.2 — Validated `models/config.json`; it selects `llama3.2:3b`, localhost Ollama, context 4096, temperature 0.2, and seed 42.
  - Stage 6.3 — Added an async HTTPX Ollama client with validated local-only settings and readable connection errors; Python syntax compilation passed.
- **Known issues:** The bare `ollama` command is not resolved by PowerShell; use the full executable path. Keep the Ollama server terminal open during local requests.
- **Deferred:** None.
- **Exact next step:** Pull the active branch and test `python -m lego.cli --message ...` with the local model.

The repository now has the package identity, model configuration, async Ollama client, system prompt, and terminal chat entry point. Model weights remain outside the repository and user profile. Ollama is bound to `127.0.0.1:11434`, with CPU inference and a 4096-token request context.
