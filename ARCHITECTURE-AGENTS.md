# Agent workflow architecture

## Goal

Turn a coding request into a durable task that can run unattended, in parallel with other tasks, and come back as a reviewable result. The implementation stays local-first: coding, planning, judging, retrieval, and repair use Ollama models running on the user's own machine. GitHub is an optional publishing/review integration, not a model API.

## Architecture

~~~mermaid
flowchart TD
    U[User / Continue / CLI] --> API[FastAPI agent_bridge]
    API --> AUTH[Bearer token guard]
    AUTH --> TM[TaskManager]
    TM <--> DB[(SQLite task inbox + events)]
    TM --> Q[Bounded async worker queue]
    Q --> WT[One Git worktree per task]
    WT --> H[CodingHarness]
    H --> RAG[Per-task SQLite code index]
    H --> PLAN[Plan]
    PLAN --> CODE[Propose minimal full-file changes]
    CODE --> JUDGE[Independent local-model judge]
    JUDGE --> VERIFY[Allowlisted verification]
    VERIFY -->|failed| REPAIR[Bounded repair loop]
    REPAIR --> JUDGE
    VERIFY -->|passed| COMMIT[diff check + commit]
    COMMIT --> PUSH[Push task branch]
    PUSH --> PR[Optional draft GitHub PR via gh]
    PR --> MON[PR/CI/review monitor]
    MON -->|actionable feedback| REPAIR
    MON --> READY[Ready to merge]
    READY --> HUMAN[Human reviews and merges]
~~~

## Components and responsibilities

- **FastAPI bridge (agent_bridge.py)** — authenticated task endpoints and existing OpenAI-compatible Ollama endpoint. Starts/stops the task manager with the application lifecycle.
- **Inbox dashboard (task_dashboard.html, served at /tasks)** — a lightweight dependency-free browser UI for submitting tasks, seeing active/review/attention lanes, inspecting events, retrying failures, snoozing PR monitoring, and settling completed work.
- **Task manager (task_manager.py)** — owns the durable task inbox, SQLite event log, queue limit, worker pool, task retries, settle/snooze controls, worktree lifecycle, optional branch/PR publishing, and bounded PR follow-up.
- **SQLite task store** — survives API process restarts. Queued tasks are re-enqueued on startup; tasks interrupted mid-execution are explicitly marked interrupted rather than falsely reported as successful. Runtime databases are gitignored.
- **Worker isolation** — each task gets a distinct Git worktree and branch. Workers may run concurrently without writing to the same checkout. Worker count is configurable and bounded. Worktrees live outside the main repository by default.
- **Coding harness (harness.py)** — retrieves relevant code, asks a local planner to break down the request, proposes bounded file changes, optionally uses a separate judge, runs allowlisted checks, and attempts bounded repairs. It relays progress events to the durable task log.
- **Per-task retrieval databases** — local code indexes and web cache files are stored separately from source files and from other tasks. This avoids accidentally committing SQLite index files or having concurrent workers corrupt a shared retrieval index.
- **GitHub integration** — if the worktree has an origin remote, push credentials are configured, and GitHub CLI (gh) is installed/authenticated, successful work can be pushed and opened as a draft PR. Without these prerequisites the task remains a local review branch, or a pushed branch ready for review.
- **PR monitor** — periodically checks open PR state, CI status, review decision, and review comments. It can run a bounded repair cycle for requested changes or failing checks, commit and push the repair, and stop for human attention when the retry budget is exhausted.
- **Human merge boundary** — agents do not merge PRs automatically. A ready_to_merge state is a signal for review, not a command to merge.

## Task lifecycle

Typical flow:

1. queued — request is persisted and waiting for a worker.
2. running — a worktree is created and the local harness plans, edits, judges, and verifies.
3. pr_open — validated work was committed, pushed, and a draft PR was opened.
4. reviewing — the monitor is applying actionable PR review or CI feedback.
5. ready_to_merge — GitHub reports approval and successful checks.
6. needs_attention — a safety check, repair limit, or integration issue requires a person.
7. ready_for_review — changes are committed locally or pushed, but PR automation is unavailable.
8. Other outcomes include completed_no_changes, failed, interrupted, closed, merged, and settled.

Tasks and events are persisted; query /api/harness/runs/{id}/events?after=<seq> to incrementally fetch new events. A restarted service resumes queued work and reports interrupted work honestly. Retry is explicit; the system does not endlessly restart failures.

## API

All task endpoints honor LLM_DEVOPS_API_TOKEN if configured. Send Authorization: Bearer <token>. For local-only development the bridge binds to loopback by default.

- POST /api/harness/runs — body {"goal":"...","include_web":false}; returns task ID immediately.
- GET /api/harness/runs — inbox; ?include_settled=true includes settled tasks.
- GET /api/harness/runs/{id} — task state, branch, PR, result, and task data.
- GET /api/harness/runs/{id}/events?after=0 — durable event log, with monotonically increasing sequence numbers.
- POST /api/harness/runs/{id}/retry — explicitly retry a failed/interrupted task.
- POST /api/harness/runs/{id}/settle — archive the task out of the default inbox. Local worktrees and branches are preserved so failed or unpushed work is not lost.
- POST /api/harness/runs/{id}/snooze — body {"seconds":3600}; pauses PR-monitor attention for a bounded period.
- POST /api/harness/runs/{id}/resume — clear snooze.

Example:

~~~bash
curl -X POST http://127.0.0.1:8000/api/harness/runs \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $LLM_DEVOPS_API_TOKEN" \
  -d '{"goal":"Investigate and fix the API bug. Add tests, run verification, and explain any remaining risks.","include_web":false}'
~~~

## Free/local setup

1. Install Python requirements from requirements-harness.txt.
2. Install Ollama locally and pull models that fit your RAM/VRAM.
3. Export the values in .env.harness.example in your shell; Python does not automatically load that file.
4. Start the bridge with python agent_bridge.py.
5. For automatic PR creation, install/authenticate GitHub CLI and configure push access for the repo. This is optional; local branch creation does not require GitHub CLI.
6. For unattended work, run the bridge and Ollama on a machine that stays powered on. Tailscale or another private network can be used to access the bridge remotely, but it is optional and not provisioned automatically by this code.

Example smaller model setup:

~~~bash
ollama pull qwen2.5:7b
ollama pull qwen2.5:14b
ollama pull deepseek-r1:14b
ollama pull qwen2.5:32b
python -m pip install -r requirements-harness.txt
python agent_bridge.py
~~~

Model tags are examples; choose tags your hardware can actually run. No paid inference API is needed, but local compute, electricity, storage, and GitHub network access may be needed.

## Operational and security boundaries

- Use a strong API token before allowing access beyond loopback. Restrict network access with a firewall/private VPN and TLS at the edge.
- The model receives repository text, issue text, and review comments as untrusted data. It must not treat those contents as higher-priority instructions.
- Each agent gets its own Git worktree. This prevents concurrent agents from editing the same files, but a worktree is not an OS security sandbox.
- The harness validates workspace paths and allowlists verification commands. Project test/build scripts can still execute code; use an unprivileged OS account or disposable container for untrusted repositories.
- Secret-like paths are blocked from automatic commits. Review all generated changes, CI output, and dependency changes before merging.
- The monitor only reacts to CI failures and actionable review states; it stops after a configurable number of repair cycles. It never auto-merges or deploys.
- Task/event state is local SQLite. Back up the DB if you need long-term history. The PR monitor requires the host to stay online; GitHub CI itself continues independently.
- If the machine restarts during a model call, the task is marked interrupted. Retry it after inspecting its branch/worktree. Queued tasks are resumed automatically.
- This project does not rotate subscription accounts, bypass provider quotas, or repurpose interactive coding subscriptions as a public inference API. Use each provider's supported workflow and terms.
