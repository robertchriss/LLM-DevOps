"""Development runner for the generated Kubernetes quiz app.

This runner does not silently rewrite application files after runtime failures.
It reports failures and leaves repair decisions to the orchestrator, keeping the
working tree reviewable. Configure credentials through environment variables.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_CONTAINER = os.getenv("LLM_DEVOPS_DB_CONTAINER", "k8s-quiz-db")
DB_IMAGE = os.getenv("LLM_DEVOPS_DB_IMAGE", "postgres:15-alpine")
PGUSER = os.getenv("PGUSER", "llm_devops")
PGPASSWORD = os.getenv("PGPASSWORD", "")
PGDATABASE = os.getenv("PGDATABASE", "k8s_quiz")
PGPORT = os.getenv("PGPORT", "5432")
BACKEND_PORT = os.getenv("PORT", "5000")
STARTUP_TIMEOUT_SECONDS = int(os.getenv("LLM_DEVOPS_STARTUP_TIMEOUT", "30"))


def run_checked(command: list[str], *, cwd: Path | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    if not shutil.which(command[0]):
        raise RuntimeError(f"Required executable not found: {command[0]}")
    return subprocess.run(
        command, cwd=str(cwd or ROOT), capture_output=True, text=True,
        timeout=timeout, check=True, shell=False,
    )


def ensure_postgres_running() -> None:
    """Start/create a local development DB. Password must be explicitly configured."""
    if not PGPASSWORD:
        raise RuntimeError(
            "Set PGPASSWORD in your environment before starting PostgreSQL. "
            "The runner intentionally has no hardcoded database password."
        )
    if not shutil.which("docker"):
        raise RuntimeError("Docker CLI is required to manage the development database.")

    running = run_checked([
        "docker", "ps", "--filter", f"name=^{DB_CONTAINER}$", "--format", "{{.Names}}"
    ])
    if DB_CONTAINER in running.stdout.splitlines():
        print(f"PostgreSQL container {DB_CONTAINER} is already running.")
    else:
        existing = run_checked([
            "docker", "ps", "-a", "--filter", f"name=^{DB_CONTAINER}$", "--format", "{{.Names}}"
        ])
        if DB_CONTAINER in existing.stdout.splitlines():
            run_checked(["docker", "start", DB_CONTAINER])
        else:
            # Publish only to loopback; don't expose the development DB on all interfaces.
            run_checked([
                "docker", "run", "-d", "--name", DB_CONTAINER,
                "-p", f"127.0.0.1:{PGPORT}:5432",
                "-e", f"POSTGRES_USER={PGUSER}",
                "-e", f"POSTGRES_PASSWORD={PGPASSWORD}",
                "-e", f"POSTGRES_DB={PGDATABASE}",
                DB_IMAGE,
            ])
    schema_path = ROOT / "app" / "db" / "schema.sql"
    if schema_path.is_file():
        # For a dev runner this applies the schema. Prefer versioned migrations in production.
        with schema_path.open("r", encoding="utf-8") as handle:
            schema_sql = handle.read()
        proc = subprocess.run(
            ["docker", "exec", "-i", DB_CONTAINER, "psql", "-v", "ON_ERROR_STOP=1",
             "-U", PGUSER, "-d", PGDATABASE],
            input=schema_sql, text=True, capture_output=True, timeout=60, check=False, shell=False,
        )
        if proc.returncode:
            raise RuntimeError(f"Database schema application failed:\n{proc.stderr[-4000:]}")
        print("Database schema applied successfully.")


def check_http_endpoint(url: str, timeout: int = 2) -> tuple[bool, str]:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "LLM-DevOps-dev-runner"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(10000).decode("utf-8", errors="replace")
            return response.status == 200, body
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}: {exc.reason}"
    except Exception as exc:
        return False, str(exc)


async def wait_for_health(process: subprocess.Popen, url: str) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    last_message = "No response yet"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Backend exited with code {process.returncode}")
        healthy, message = check_http_endpoint(url)
        if healthy:
            print(f"Backend health check passed: {url} ({message})")
            return
        last_message = message
        await asyncio.sleep(1)
    raise TimeoutError(f"Backend did not become healthy within {STARTUP_TIMEOUT_SECONDS}s: {last_message}")


async def main() -> None:
    ensure_postgres_running()

    print("Running the code-generation orchestrator...")
    run_checked(["python", "orchestrator.py"], cwd=ROOT, timeout=1800)

    backend_dir = ROOT / "app" / "backend"
    server_file = backend_dir / "server.js"
    if not server_file.is_file():
        raise FileNotFoundError(f"Backend file not found: {server_file}")

    if not shutil.which("node"):
        raise RuntimeError("Node.js is required to start the backend.")
    process = subprocess.Popen(
        ["node", "server.js"],
        cwd=str(backend_dir),
        stdout=None,
        stderr=None,
        shell=False,
    )
    try:
        await wait_for_health(process, f"http://127.0.0.1:{BACKEND_PORT}/healthz")
        print("Backend is healthy. Functional API and frontend tests still need to be run.")
        print("Press Ctrl+C to stop the runner.")
        while process.poll() is None:
            await asyncio.sleep(1)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Runner stopped.")
