# Autonomous local-agent workflow

This workflow turns a problem into a persistent background task: create an isolated Git worktree, let local agents plan/edit/review/test, commit only verified changes, optionally open a draft GitHub PR, and monitor CI/review feedback with a bounded repair loop. You can start multiple tasks and check back when they need attention.

Read [ARCHITECTURE-AGENTS.md](ARCHITECTURE-AGENTS.md) for the full component diagram, lifecycle, and safety boundaries.

## Free/local setup

Install dependencies:

~~~bash
python -m pip install -r requirements-harness.txt
~~~

Install Ollama and pull models that fit your hardware:

~~~bash
ollama pull qwen2.5:7b
ollama pull qwen2.5:14b
ollama pull deepseek-r1:14b
ollama pull qwen2.5:32b
~~~

Export the variables in .env.harness.example in your shell before starting the bridge; Python does not load that file automatically. Configure at least:

- PROJECT_WORKSPACE: Git repository root to use as the worktree base.
- OLLAMA_BASE_URL: local Ollama endpoint.
- OLLAMA_FAST_MODEL, OLLAMA_WORKER_MODELS, OLLAMA_JUDGE_MODEL: model tags available in Ollama.
- USE_JUDGE=true: require an independent judge pass before applying each proposed patch.
- LLM_DEVOPS_TASK_WORKERS: maximum simultaneous worktrees/model tasks (default 2; choose based on RAM/VRAM).
- LLM_DEVOPS_TASK_DB and LLM_DEVOPS_WORKTREE_ROOT: persistent task state and worktree locations.
- LLM_DEVOPS_PR_MONITOR=true and LLM_DEVOPS_MAX_REVIEW_CYCLES=3: enable bounded PR follow-up.

Start the service:

~~~bash
python agent_bridge.py
~~~

Open http://127.0.0.1:8000/tasks for the inbox dashboard. It lets you submit tasks, see working/review/attention lanes, inspect recent events, retry failed tasks, snooze PR monitoring, and settle tasks out of your inbox. The API remains available for scripts and integrations.

The bridge binds to 127.0.0.1:8000 by default. Set a strong LLM_DEVOPS_API_TOKEN before exposing it beyond loopback. Use a firewall and private network/TLS for remote access. The bridge and Ollama must stay running for unattended local tasks.

For an always-on Linux host, see [deploy/llm-devops-agent.service.example](deploy/llm-devops-agent.service.example) and [deploy/llm-devops-agent.env.example](deploy/llm-devops-agent.env.example). Edit the user and paths, create writable state/worktree directories, install the virtual environment and dependencies, put the real token in a protected environment file with mode 600, then enable the systemd unit. Keep Uvicorn at one worker; this queue is a single-process service. For remote access, prefer a private Tailscale network or Tailscale Serve rather than binding the API to a public interface.

## Submit work and check the inbox

~~~bash
curl -X POST http://127.0.0.1:8000/api/harness/runs \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $LLM_DEVOPS_API_TOKEN" \
  -d '{"goal":"Investigate the bug, implement a minimal fix, add regression tests, run verification, and report remaining risks.","include_web":false}'
~~~

The API returns a task ID immediately. Use it to check progress:

~~~bash
curl -H "Authorization: Bearer $LLM_DEVOPS_API_TOKEN" http://127.0.0.1:8000/api/harness/runs
curl -H "Authorization: Bearer $LLM_DEVOPS_API_TOKEN" http://127.0.0.1:8000/api/harness/runs/<TASK_ID>
curl -H "Authorization: Bearer $LLM_DEVOPS_API_TOKEN" 'http://127.0.0.1:8000/api/harness/runs/<TASK_ID>/events?after=0'
~~~

The events endpoint returns durable events with sequence numbers; pass ?after=<last-seq> to fetch only newer events.

## Task controls

- POST /api/harness/runs/{id}/retry — explicitly retry a failed/interrupted task.
- POST /api/harness/runs/{id}/settle — archive a task out of the default inbox without deleting its worktree or branch. Active tasks cannot be settled.
- POST /api/harness/runs/{id}/snooze with {"seconds":3600} — pause PR-monitor attention temporarily.
- POST /api/harness/runs/{id}/resume — resume PR monitoring.
- GET /api/harness/runs?include_settled=true — include settled tasks.

## Automatic GitHub workflow (optional)

Automatic PR creation requires:
1. Git installed and the source repository has an origin remote.
2. Push access to that repository from this machine.
3. GitHub CLI (gh) installed and authenticated.
4. CI configured on the repository if you want CI feedback monitored.

Successful work is committed on an agent/task-* branch in a separate worktree. If the prerequisites are met, the branch is pushed and a **draft PR** is opened. The monitor checks the PR, review decision, review comments, and CI status. It can run a bounded repair cycle and push a follow-up commit. After the configured repair limit, it changes the task to needs_attention.

The system **never auto-merges or deploys**. ready_to_merge means the monitor saw an approval and successful checks; review the diff and CI before merging. If gh or push access is unavailable, the task remains ready_for_review with its local branch or pushed branch information.

## Parallelism and recovery

Every task has its own Git worktree and its own retrieval databases. Concurrent agents therefore do not write into the same checkout or index. LLM_DEVOPS_TASK_WORKERS defaults to 2 and is capped to prevent accidental unbounded spawning. Use a value appropriate to your machine; local model memory is often the limiting resource.

Task metadata and events are stored in SQLite. Queued tasks resume after service restart; tasks interrupted during execution are marked interrupted and can be retried. PR monitoring runs only while the bridge is online. The task manager does not silently restart a failed task forever.

## Safety boundaries

- This uses local Ollama models; it does not need paid inference API keys. Compute, storage, electricity, and model downloads still have costs.
- A Git worktree is isolation from other agent edits, **not an OS sandbox**. Tests/build scripts can execute code. Use an unprivileged account or disposable container for untrusted repositories.
- Workspace path validation, command allowlists, independent judging, diff checks, and secret-path checks reduce risk but do not prove code is safe.
- API bearer auth is optional for backward compatibility. Configure LLM_DEVOPS_API_TOKEN before allowing network access beyond loopback.
- Generated changes need human review. Do not give agents permission to auto-merge or deploy until you have separate safeguards and rollback procedures.
- The implementation does not bypass provider quotas, rotate accounts, or route interactive subscriptions through unsupported clients. Use tools within their providers' terms.

## Focused tests

~~~bash
python -m pytest tests/test_harness_paths.py tests/test_task_manager.py -q
~~~

Run these tests in your local environment. The task-manager tests use temporary SQLite state and do not require Ollama. I have not claimed a passing test run from GitHub editing alone.
