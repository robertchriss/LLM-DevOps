# Autonomous coding harness

This adds a bounded plan → propose complete-file changes → judge → apply → verify → repair loop.

## Safety boundary

Set `PROJECT_WORKSPACE` to the repository root. The harness rejects absolute paths, traversal, common dependency/build directories, and symlink path components. File changes are written only beneath that root. The verification runner uses argument arrays rather than a shell and has an executable allowlist.

**Important:** A process launched by an allowed program can still do arbitrary work. For example, project test/build scripts execute code. Run this harness only against a trusted repository in a disposable branch/worktree or container. The workspace guard is not an OS sandbox and cannot guarantee protection against malicious code, filesystem races, or a process intentionally escaping its working directory. Keep the API on localhost. Review the diff and commit yourself.

## Install and configure

Install the packages in `requirements-harness.txt`. Set environment variables from `.env.harness.example`; this sample does not load `.env` automatically unless you add `python-dotenv` and call `load_dotenv()` before reading settings.

`PROJECT_WORKSPACE` must be the exact repository directory to modify. Do not set it to a parent folder containing several projects.

## API integration

Import `CodingHarness` into `agent_bridge.py`, construct it using your environment settings, and add an endpoint that awaits `harness.run(goal, include_web)`. Expose run status and events from `harness.runs` and `harness.events` in your API. Do not replace the existing `/v1/chat/completions` endpoint: Continue uses it for normal chat completions.

Example construction:

```python
from harness import CodingHarness

coding_harness = CodingHarness(
    root=os.getenv("PROJECT_WORKSPACE", "."),
    ollama_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    fast_model=os.getenv("OLLAMA_FAST_MODEL", "qwen2.5:7b"),
    worker_models=os.getenv("OLLAMA_WORKER_MODELS", "qwen2.5:14b,deepseek-r1:14b").split(","),
    judge_model=os.getenv("OLLAMA_JUDGE_MODEL", "qwen2.5:32b"),
    use_judge=os.getenv("USE_JUDGE", "true").lower() in {"1", "true", "yes"},
    max_iterations=int(os.getenv("HARNESS_MAX_ITERATIONS", "3")),
    max_tasks=int(os.getenv("HARNESS_MAX_TASKS", "12")),
    command_timeout=int(os.getenv("HARNESS_COMMAND_TIMEOUT", "120")),
    model_timeout=int(os.getenv("HARNESS_MODEL_TIMEOUT", "180")),
)
```

Endpoint sketch:

```python
from pydantic import BaseModel, Field

class HarnessRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=12000)
    include_web: bool = False

@app.post("/api/harness/run")
async def start_harness(req: HarnessRequest):
    # This waits for completion; for background execution, wrap in asyncio.create_task
    # and return a run id, as the existing /api/command endpoint does.
    return await coding_harness.run(req.goal, req.include_web)
```

This synchronous endpoint example is intentionally simple. To stream progress, adapt the existing SSE endpoint to read `coding_harness.events[run_id]`. For a production UI, make the run backgrounded and expose `/api/harness/runs/{run_id}` and `/api/harness/runs/{run_id}/events`.

## Current limitations

- Uses the fast model to plan and propose edits; judge checks the proposed patch. Worker-model consensus and independent code review can be added later.
- Model output must be JSON with complete file contents; malformed output fails closed.
- Verification commands must be explicitly allowlisted. Avoid letting model output choose arbitrary shell commands.
- Take a backup/branch before the first run. Inspect diffs before committing.
