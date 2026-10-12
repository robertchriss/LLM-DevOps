# LLM-DevOps

Local multi-model software orchestration using Ollama and LiteLLM.

## Architecture

- Qwen 14B and DeepSeek R1 14B produce independent proposals in parallel.
- Qwen 32B reviews/synthesizes proposals.
- The Python orchestrator runs limited syntax checks before writing a generated file.
- The FastAPI bridge offers an OpenAI-compatible chat endpoint and workspace-limited file routes.
- The development runner can start PostgreSQL and the Node backend.

A model's approval is not proof of correctness. Run the project's unit, integration, and security tests before using generated code.

## Requirements

- Python 3.10+
- Ollama with the configured models already pulled
- Node.js for JavaScript syntax checks and the sample backend
- Docker only if using `agent_runner.py` to manage PostgreSQL

## Setup

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set a unique `PGPASSWORD`. Environment variables are not automatically loaded from `.env` by Python; export them in your shell or use a trusted environment loader. Do not commit secrets.

Verify Ollama is reachable at `http://localhost:11434` and pull the models you intend to use.

## Generate the sample application

From the repository root:

```bash
python orchestrator.py
```

This keeps the previous no-argument behavior and generates the sample quiz application files sequentially.

## Generate one file for a custom task

```bash
python orchestrator.py --prompt "Create a FastAPI health endpoint" --output "scratch/health.py"
```

The output path must be relative to `LLM_DEVOPS_WORKSPACE` (defaults to the current directory).

## Run the API bridge

```bash
python agent_bridge.py
```

The server binds to `127.0.0.1:8000` by default. Set `LLM_DEVOPS_API_TOKEN` before exposing any endpoint beyond loopback. For remote deployment, use TLS, authentication, firewall rules, and a restricted service account.

## Run the development runner

Set `PGPASSWORD` and other database variables first, then:

```bash
python agent_runner.py
```

The runner applies `app/db/schema.sql` when present and starts the backend. It does not silently overwrite code in response to runtime failures. Health-check success does not replace functional tests.

## Security notes

- Do not expose the API bridge publicly without authentication and TLS.
- Keep generated-code execution in an unprivileged container or disposable VM.
- Workspace path checks are not a substitute for OS isolation.
- Never execute shell commands supplied by a model without a trusted allowlist and validation.
- Use unique development credentials and secret management in production.
- Add database migrations, tests, linting, type checks, CI, and audit logging before production use.
