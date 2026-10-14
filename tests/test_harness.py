import pytest
import requests
import json

BRIDGE_URL = "http://127.0.0.1:8000/api/command"

def test_sql_generation_validity():
    """Harness Test 1: Verify agent bridge generates valid SQL structure without conversational fluff."""
    payload = {
        "prompt": "Create a PostgreSQL table named 'test_users' with an id and name. Return ONLY valid SQL inside a markdown code block.",
    }
    res = requests.post(BRIDGE_URL, json=payload, timeout=120)
    assert res.status_code == 200, "Agent bridge endpoint unreachable or returned non-200"
    
    content = res.json().get("content", "")
    assert "CREATE TABLE" in content.upper(), "Generated payload missing SQL CREATE TABLE command"
    assert "test_users" in content, "Generated payload missing target table name"
    assert "Here is your SQL" not in content, "Generated payload contains prohibited conversational prose"

def test_agent_file_write_security():
    """Harness Test 2: Verify path traversal attempt is blocked by security bounds."""
    payload = {
        "prompt": "Write malicious content",
        "target_file": "../../../etc/passwd"
    }
    res = requests.post(BRIDGE_URL, json=payload, timeout=30)
    assert res.status_code == 400, "Security check failed: Bridge allowed unsafe path target"

import subprocess
import httpx
import re
from rag_engine import ingest_spec_and_docs, get_relevant_context

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:32b"

def extract_code(text: str) -> str:
    """Extract code from markdown blocks."""
    blocks = re.findall(r"```(?:javascript|js|jsx)?\n(.*?)```", text, flags=re.DOTALL)
    return blocks[0].strip() if blocks else text

def run_harness() -> tuple[bool, str]:
    """Run pytest and capture the output to feed back to the LLM."""
    result = subprocess.run(
        ["pytest", "tests/test_harness.py", "--disable-warnings"], 
        capture_output=True, 
        text=True
    )
    return result.returncode == 0, result.stdout + "\n" + result.stderr

def agentic_loop(initial_prompt: str, target_file: str, max_iterations: int = 5):
    print(f"🚀 Starting Test-Driven Autonomous Loop for: {target_file}")
    
    # 1. RAG Retrieval Step: Ground the prompt in reality
    print("🔍 Retrieving context from spec.md...")
    context = get_relevant_context(initial_prompt)
    
    system_prompt = f"""
    You are a senior developer. Output ONLY valid code inside markdown blocks.
    
    STRICT ARCHITECTURAL CONTEXT:
    {context}
    
    If the prompt violates this context, adapt the code to fit the architecture.
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": initial_prompt}
    ]
    
    # 2. Execution & Evaluation Loop
    for attempt in range(1, max_iterations + 1):
        print(f"\n--- Iteration {attempt}/{max_iterations} ---")
        print("🤖 Generating code...")
        
        res = httpx.post(OLLAMA_URL, json={"model": MODEL, "messages": messages, "stream": False}, timeout=120)
        llm_reply = res.json()["message"]["content"]
        
        code = extract_code(llm_reply)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"🔨 Wrote changes to {target_file}")
        
        print("🧪 Running Harness...")
        passed, harness_output = run_harness()
        
        if passed:
            print("✅ SUCCESS! Harness passed. The best answer was applied.")
            break
        else:
            print("❌ Harness failed. Feeding trace back to the LLM...")
            messages.append({"role": "assistant", "content": llm_reply})
            messages.append({
                "role": "user", 
                "content": f"The test failed. Analyze this stack trace and rewrite the code to fix it:\n\n{harness_output}"
            })
            
    if not passed:
        print(f"⚠️ Reached max iterations ({max_iterations}). Manual intervention required.")

if __name__ == "__main__":
    # Seed the vector database with your master spec on startup
    ingest_spec_and_docs(["spec.md"])
    
    task = """
    Write a React component for App.js that maps over a list of 'quizzes' fetched from the backend. 
    It must handle the 'Cannot read properties of undefined' error by including a loading state or optional chaining.
    """
    agentic_loop(task, target_file="app/frontend/src/App.js")

# Append to the bottom of tests/test_harness.py

def test_quiz_ui_interaction(page):
    """
    Harness Test 4: Open browser, click 'Take Quiz', and verify React doesn't crash.
    Requires frontend running on localhost:3000.
    """
    import pytest

    console_errors = []
    
    # 1. Listen for hidden browser console errors (like mapping undefined)
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda err: console_errors.append(err.message))

    # 2. Navigate to the local React app
    try:
        response = page.goto("http://localhost:3000", timeout=5000)
        assert response.ok, "Frontend is not running. Start it with 'npm start'."
    except Exception as e:
        pytest.fail(f"Could not connect to React frontend: {e}")

    # 3. Find and click the 'Take Quiz' button
    try:
        quiz_button = page.get_by_text("Take Quiz", ignore_case=True).first
        quiz_button.wait_for(state="visible", timeout=10000)
        quiz_button.click()
    except Exception:
        pytest.fail("The 'Take Quiz' button was not found on the page or is not visible.")

    # 4. Wait for React state to update, then scrape the screen for error overlays
    page.wait_for_timeout(1000)
    body_text = page.locator("body").inner_text()
    
    # Check for Webpack/React error overlays in the DOM
    if "Cannot read properties" in body_text or "TypeError" in body_text:
        pytest.fail(f"React crashed on screen after clicking button. Found in DOM: {body_text[:300]}")

    # 5. Fail if we caught any silent console errors
    if console_errors:
        pytest.fail(f"Browser console errors detected after clicking: {console_errors}")