# Autonomous coding harness

This provides a bounded local-model coding loop: retrieve project context → plan → propose complete-file changes → judge → apply → verify → repair. The API bridge can run long tasks in the background and report progress while you work on something else.

## Free/local model setup

The default setup uses Ollama on your own machine. It does not require paid model API keys or usage-based API billing. Downloading and running models still requires disk space, memory, and compute.

Install the Python requirements:

```bash
python -m pip install -r requirements-harness.txt
```

Pull the local models you want to use (choose models that fit your hardware):

```bash
ollama pull qwen2.5:7b
ollama pull qwen2.5:14b
ollama pull deepseek-r1:14b
ollama pull qwen2.5:32b
```

Configure the variables in `.env.harness.example` in your shell before starting the bridge. Python does not load that file automatically. In particular:

- `PROJECT_WORKSPACE`: exact repository directory the agent may edit.
- `OLLAMA_BASE_URL`: local Ollama endpoint.
- `OLLAMA_FAST_MODEL`, `OLLAMA_WORKER_MODELS`, `OLLAMA_JUDGE_MODEL`: model names already pulled into Ollama.
- `USE_JUDGE=true`: require a separate judge pass before applying changes.
- `HARNESS_MAX_ITERATIONS`, `HARNESS_MAX_TASKS`: bound repair and planning loops.

Start the bridge:

```bash
python agent_bridge.py
```

The default bind is `127.0.0.1:8000`. Set a strong `LLM_DEVOPS_API_TOKEN` before making the API reachable from another machine. Do not expose it to the public internet without authentication, TLS, firewall restrictions, and a restricted service account.

## Submit a long-running task

Submit a goal and return immediately with a run ID:

```bash
curl -X POST http://127.0.0.1:8000/api/harness/runs \
  -H 'Content-Type: application/json' \
  -d '{"goal":"Review the API for bugs, add focused tests, and fix issues without changing unrelated behavior.","include_web":false}'
```

The response includes `id`, `status_url`, and `events_url`. Poll them while the task runs:

```bash
curl http://127.0.0.1:8000/api/harness/runs/<RUN_ID>
curl http://127.0.0.1:8000/api/harness/runs/<RUN_ID>/events
curl http://127.0.0.1:8000/api/harness/runs
```

Add the same `Authorization: Bearer <LLM_DEVOPS_API_TOKEN>` header to requests if a token is configured. The events endpoint returns the current event list; poll it periodically to see planning, edits, verification, and repair attempts. `include_web` defaults to false so a normal coding task can stay local and avoid external search.

## Concurrency and task state

The bridge accepts multiple queued tasks but deliberately runs them one at a time against the configured workspace. This prevents agents from overwriting each other's files. Run status and events are kept in memory, so restarting the bridge loses the history. True parallel execution should use a separate Git worktree or disposable clone per task; do not point multiple independent writers at the same checkout.

This implementation does not automatically create, merge, or babysit GitHub pull requests. After reviewing the diff and tests, create a branch/PR using your normal Git workflow. PR automation, independent reviewer agents, and post-merge rollback monitoring are follow-on steps, not features this API claims to provide.

## Safety boundary

The harness rejects absolute paths, traversal, common dependency/build directories, and symlink path components. File changes are written only beneath `PROJECT_WORKSPACE`. Verification commands use argument arrays rather than a shell and have an executable allowlist.

**This is not an OS sandbox.** A process launched by an allowed program can still execute project code; test and build scripts may have arbitrary side effects. Run against a trusted repository in a disposable branch/worktree or container. Review the diff and test output before merging. Model approval is not proof of correctness.

## Verification

Run the isolated harness/path tests:

```bash
python -m pytest tests/test_harness_paths.py -q
```

The repository also contains tests that expect a running bridge, local Ollama models, browser tooling, or database services; those are integration tests and are not covered by the command above.
