import asyncio
import os
import subprocess
import time
import urllib.request
import urllib.error
from litellm import acompletion

# Model configurations matching your local setup
QWEN_32B = "ollama/qwen2.5:32b"
OLLAMA_BASE = "http://localhost:11434"


def ensure_postgres_running():
    """Checks if PostgreSQL Docker container is running, or spins it up."""
    print("🐳 Verifying PostgreSQL Docker Container...")

    res = subprocess.run(
        ["docker", "ps", "--filter", "name=k8s-quiz-db", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
    )

    if "k8s-quiz-db" in res.stdout:
        print("✅ PostgreSQL container is already running.")
    else:
        stopped_res = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=k8s-quiz-db", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        if "k8s-quiz-db" in stopped_res.stdout:
            print("🔄 Starting existing PostgreSQL container...")
            subprocess.run(["docker", "start", "k8s-quiz-db"], check=True)
        else:
            print("🚀 Creating and launching new PostgreSQL container...")
            subprocess.run(
                [
                    "docker", "run", "-d",
                    "--name", "k8s-quiz-db",
                    "-p", "5432:5432",
                    "-e", "POSTGRES_USER=postgres",
                    "-e", "POSTGRES_PASSWORD=postgres",
                    "-e", "POSTGRES_DB=k8s_quiz",
                    "postgres:15-alpine",
                ],
                check=True,
            )
            time.sleep(4)  # Wait for DB engine startup

    # Apply database schema migration
    print("📜 Seeding database schema from app/db/schema.sql...")
    schema_path = os.path.join("app", "db", "schema.sql")

    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        subprocess.run(
            ["docker", "exec", "-i", "k8s-quiz-db", "psql", "-U", "postgres", "-d", "k8s_quiz"],
            input=schema_sql,
            text=True,
            check=True,
        )
        print("✅ Database schema successfully seeded!")
    else:
        print(f"⚠️ Schema file not found at '{schema_path}'. Skipping initial seeding.")


async def query_judge_fix(file_path: str, current_code: str, error_log: str) -> str:
    """Sends runtime errors back to Qwen 32B to generate a bugfix patch."""
    prompt = (
        f"The application file '{file_path}' failed during runtime execution.\n\n"
        f"CURRENT CODE:\n{current_code}\n\n"
        f"RUNTIME ERROR / LOGS:\n{error_log}\n\n"
        "INSTRUCTIONS:\n"
        "Analyze the error and fix the code completely.\n"
        "Return ONLY the updated code inside markdown code blocks. Do not write introductory text."
    )

    response = await acompletion(
        model=QWEN_32B,
        messages=[
            {"role": "system", "content": "You are an expert full-stack debugger and auto-healing agent."},
            {"role": "user", "content": prompt},
        ],
        api_base=OLLAMA_BASE,
    )
    raw = response.choices[0].message.content
    if "```" in raw:
        lines = raw.split("```")[1].split("\n")
        if lines[0].strip() in ["javascript", "js", "json", "html", "css", "python"]:
            lines = lines[1:]
        return "\n".join(lines).strip()
    return raw.strip()


def check_http_endpoint(url: str, timeout: int = 2) -> tuple[bool, str]:
    """Pings an HTTP endpoint to verify service health."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                return True, response.read().decode("utf-8")
            return False, f"HTTP Status {response.status}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP Error {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)


async def auto_heal_backend():
    """Boots backend server, monitors runtime, and patches code until HTTP 200 OK."""
    print("\n🚀 Autonomous Agent: Verifying Backend Server...")
    max_retries = 3
    backend_dir = os.path.join(os.getcwd(), "app", "backend")
    server_file = os.path.join(backend_dir, "server.js")

    for attempt in range(1, max_retries + 1):
        print(f"🔄 Attempt {attempt}/{max_retries}: Starting Node.js server...")
        process = subprocess.Popen(
            ["node", "server.js"],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        time.sleep(3)  # Allow server initialization

        # Check if process crashed immediately
        if process.poll() is not None:
            _, stderr = process.communicate()
            print(f"❌ Backend crashed on startup:\n{stderr}")
            with open(server_file, "r", encoding="utf-8") as f:
                code = f.read()
            fixed_code = await query_judge_fix(server_file, code, stderr)
            with open(server_file, "w", encoding="utf-8") as f:
                f.write(fixed_code)
            continue

        # Probe health endpoint
        is_healthy, msg = check_http_endpoint("http://localhost:5000/healthz")
        if is_healthy:
            print("✅ Backend server is online and responding on http://localhost:5000!")
            return process
        else:
            print(f"⚠️ Health check failed: {msg}")
            process.terminate()
            with open(server_file, "r", encoding="utf-8") as f:
                code = f.read()
            fixed_code = await query_judge_fix(
                server_file, code, f"Endpoint ping failed: {msg}"
            )
            with open(server_file, "w", encoding="utf-8") as f:
                f.write(fixed_code)

    raise RuntimeError("Backend auto-healing exceeded maximum retries.")


async def main():
    print("🤖 Initializing Autonomous Multi-Agent Self-Healing Loop...")

    # Step 1: Ensure Postgres DB is active
    ensure_postgres_running()

    # Step 2: Run code generation pipeline
    print("\n📦 Generating application code files via orchestrator.py...")
    subprocess.run(["python", "orchestrator.py"], check=True)

    # Step 3: Re-apply schema in case orchestrator generated new/updated DB tables
    ensure_postgres_running()

    # Step 4: Auto-heal backend process
    backend_proc = await auto_heal_backend()

    print("\n🎉 Full pipeline operational! DB is seeded and Backend API is alive on http://localhost:5000")


if __name__ == "__main__":
    asyncio.run(main())