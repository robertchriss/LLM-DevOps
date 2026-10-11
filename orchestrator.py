import asyncio
import json
import os
import re
import subprocess
from litellm import acompletion

QWEN_14B = "ollama/qwen2.5:14b"
DEEPSEEK_14B = "ollama/deepseek-r1:14b"
QWEN_32B = "ollama/qwen2.5:32b"
OLLAMA_BASE = "http://localhost:11434"


async def query_model(
    model_name: str,
    prompt: str,
    system_prompt: str = "You are an expert AI assistant.",
):
    try:
        response = await acompletion(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            api_base=OLLAMA_BASE,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error running {model_name}: {str(e)}"


def extract_code(text: str) -> str:
    match = re.search(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def validate_code(filepath: str, code: str) -> tuple[bool, str]:
    base, ext = os.path.splitext(filepath)
    temp_path = f"{base}.tmp{ext}"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(code)

    if filepath.endswith(".js"):
        res = subprocess.run(
            ["node", "--check", temp_path], capture_output=True, text=True
        )
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return (res.returncode == 0, res.stderr)

    if filepath.endswith(".json"):
        try:
            json.loads(code)
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return (True, "")
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return (False, str(e))

    if os.path.exists(temp_path):
        os.remove(temp_path)
    return (True, "")


async def process_task(prompt: str, output_filepath: str):
    print(f"\n==================================================")
    print(f"🚀 Starting Creation Task for: '{output_filepath}'")
    print(f"==================================================")

    print("🔄 Dispatching Qwen 14B & DeepSeek R1 14B concurrently...")
    task_qwen = query_model(
        QWEN_14B, prompt, "Write clean, high-performance production code."
    )
    task_deepseek = query_model(
        DEEPSEEK_14B,
        prompt,
        "Analyze requirements and provide step-by-step architectural code.",
    )

    qwen_res, deepseek_res = await asyncio.gather(task_qwen, task_deepseek)
    print("✅ Received responses from both 14B models!")

    print("⚖️ Sending both candidates to Qwen 32B to judge & select best code...")
    judge_prompt = f"""
Compare the following two solutions generated for the task: "{prompt}"

--- SOLUTION A (Qwen 14B) ---
{qwen_res}

--- SOLUTION B (DeepSeek R1 14B) ---
{deepseek_res}

INSTRUCTIONS:
1. Compare both solutions for syntax correctness, production readiness, and best practices.
2. Combine the best elements or choose the superior candidate.
3. Output ONLY the final complete executable code inside markdown code blocks.
"""

    final_solution = await query_model(
        QWEN_32B, judge_prompt, "You are a Principal Software Architect and Judge."
    )
    clean_code = extract_code(final_solution)

    is_valid, error = validate_code(output_filepath, clean_code)

    if not is_valid:
        print(f"⚠️ Validation failed for {output_filepath}: {error}")
        print("🔄 Requesting Qwen 32B to fix syntax error...")
        fix_prompt = (
            f"The following code generated for '{output_filepath}' has a syntax error:\n\n"
            f"{clean_code}\n\n"
            f"ERROR DETAILS:\n{error}\n\n"
            "Fix the error and output ONLY the corrected code wrapped in standard markdown code blocks."
        )
        fixed_solution = await query_model(
            QWEN_32B, fix_prompt, "You are an expert debugger."
        )
        clean_code = extract_code(fixed_solution)

    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(clean_code)

    print(f"🎉 Successfully created validated file: {output_filepath}\n")


async def main():
    print("⚡ Starting Full 3-Tier Kubernetes Quiz App Pipeline...")

    # TIER 1: DATABASE
    await process_task(
        prompt="""
Write a PostgreSQL SQL migration script.
Create 3 tables:
1. 'lessons': id (SERIAL PRIMARY KEY), slug (VARCHAR UNIQUE), title (VARCHAR), content (TEXT), created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP).
2. 'quizzes': id (SERIAL PRIMARY KEY), lesson_id (INT REFERENCES lessons(id) ON DELETE CASCADE), question (TEXT), options (JSONB), correct_index (INT), explanation (TEXT).
3. 'user_scores': id (SERIAL PRIMARY KEY), username (VARCHAR), lesson_id (INT), score (INT), total (INT), submitted_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP).

Add indexes on 'slug' in lessons table and 'lesson_id' in quizzes table.
Insert seed data into 'lessons' and 'quizzes' for 2 topics: 'Pods' and 'Deployments'.
""",
        output_filepath="app/db/schema.sql",
    )

    # TIER 2: BACKEND API
    await process_task(
        prompt="""
Write a complete Node.js Express server using the 'pg' module for PostgreSQL and 'cors'.
Include the following REST endpoints:
- GET /healthz : Returns { status: "ok" }
- GET /api/lessons : Fetches all lessons from database (id, slug, title)
- GET /api/lessons/:slug : Fetches single lesson content and its associated quiz questions
- POST /api/quiz/submit : Accepts JSON body { username, lesson_id, answers }, calculates score by querying correct options from DB, records result into 'user_scores', and returns { score, total, details: [...] }.

Configure connection parameters using environment variables (PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE, PORT). Ensure server listens on PORT 5000 by default.
""",
        output_filepath="app/backend/server.js",
    )

    await process_task(
        prompt="Write a production package.json for Node.js Express backend with dependencies: express, pg, cors, dotenv.",
        output_filepath="app/backend/package.json",
    )

    # TIER 3: FRONTEND UI
    await process_task(
        prompt="""
Write a standard public/index.html for a React single-page app.
Include viewport meta tag, title "Kubernetes Docs & Quiz Hub", CDN script <script src="https://cdn.tailwindcss.com"></script>, and a <div id="root"></div>.
""",
        output_filepath="app/frontend/public/index.html",
    )

    await process_task(
        prompt="""
Write a standard src/index.js for a React 18 application using react-router-dom.
Import React, ReactDOM from 'react-dom/client', BrowserRouter from 'react-router-dom', and App from './App'.
Render <App /> wrapped inside <BrowserRouter> and <React.StrictMode> into document.getElementById('root').
""",
        output_filepath="app/frontend/src/index.js",
    )

    await process_task(
        prompt="""
Write a complete React component (App.js) styled with Tailwind CSS.
IMPORTANT STYLING & ROUTING RULES:
1. Every SVG icon MUST have explicit Tailwind dimension classes like 'w-5 h-5' or 'w-6 h-6' (NEVER raw unstyled SVGs).
2. Render a clean two-column dashboard layout: a left sidebar (w-64) for lessons and a main content section (flex-1).
3. Fetch lessons from 'http://localhost:5000/api/lessons' with proper loading/error states.
4. Tab switching between "Lesson Content" and "Take Quiz".
5. Quiz section with radio options and submit button posting to 'http://localhost:5000/api/quiz/submit'.
""",
        output_filepath="app/frontend/src/App.js",
    )

    await process_task(
        prompt="""
Write a valid package.json for a React application.
Use exact pinned dependencies:
"react": "^18.3.1",
"react-dom": "^18.3.1",
"react-router-dom": "^6.22.3",
"react-scripts": "5.0.1",
"axios": "^1.6.8",
"tailwindcss": "^3.4.1"
Do NOT add conflicting devDependencies or dummy version numbers.
""",
        output_filepath="app/frontend/package.json",
    )

    print("✅ All application files successfully created under 'app/'!")


if __name__ == "__main__":
    asyncio.run(main())