# Local RAG + DuckDuckGo for LLM-DevOps

Adds local project retrieval, optional DuckDuckGo search with SQLite TTL cache, progress events, and an OpenAI-compatible `/v1/chat/completions` endpoint backed by Ollama.

## Install

Create a virtual environment, then install dependencies:

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-rag.txt
```

Set `PROJECT_WORKSPACE` to the project directory the agent may read/write. This API can write files inside that directory, so do not expose it publicly. The example reads environment variables directly; it does not automatically load `.env`. Export variables in your shell, or install `python-dotenv` and add `from dotenv import load_dotenv; load_dotenv()` at the top of `agent_bridge.py`.

## Run

Make sure Ollama is running and that your configured models are installed. Model names in `.env.example` are examples; adjust them to your local models.

```bash
uvicorn agent_bridge:app --host 127.0.0.1 --port 8000 --reload
```

Index the workspace with `POST http://127.0.0.1:8000/api/rag/reindex`.

Submit work to `POST /api/command` with JSON such as:

```json
{"command":"Explain the current API architecture","mode":"fast","include_local":true,"include_web":false}
```

Poll the returned `status_url`; connect to `events_url` using an SSE/EventSource client to receive progress events. Modes are `fast`, `workers` (up to two models in parallel, optionally judged), and `research` (fast model with web context).

## OpenAI-compatible endpoint

`POST /v1/chat/completions` accepts a `messages` list and optional `model`, then forwards the request to Ollama. It returns a non-streaming OpenAI-style response. Configure Continue to use this local endpoint if desired.

## Tests

```bash
pytest -q
```

## Limitations and security

This is a retrieval/orchestration foundation, not a complete autonomous coding harness: it does not run shell commands, apply generated patches, or claim tests passed. SQLite FTS5 is used when available, with a lexical fallback; this is not embedding-based semantic retrieval. DuckDuckGo can rate-limit results. The indexer skips common dependency/build directories and filenames containing common secret terms, but this is not a complete secret scanner. Keep the service bound to localhost unless authentication and network controls are added.
