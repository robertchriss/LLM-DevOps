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
    
    print("🔍 Retrieving context from spec.md...")
    context = get_relevant_context(initial_prompt)
    
    system_prompt = f"""
    You are a senior React developer. Output ONLY valid, self-contained JSX code inside markdown code blocks.
    
    STRICT ARCHITECTURAL CONTEXT:
    {context}
    
    CRITICAL CONSTRAINTS:
    - Use standard `fetch('http://localhost:5000/api/lessons')` to fetch lessons.
    - Render a button for each lesson or quiz with the EXACT text "Take Quiz".
    - Do NOT stay stuck on a blank loading screen if the backend fails; render fallback sample data if fetch throws an error.
    - Output ONLY valid React code in markdown blocks.
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": initial_prompt}
    ]
    
    for attempt in range(1, max_iterations + 1):
        print(f"\n--- Iteration {attempt}/{max_iterations} ---")
        print("🤖 Generating code (timeout set to 300s)...")
        
        try:
            # Increased timeout from 120s to 300s to allow 32B model inference
            res = httpx.post(
                OLLAMA_URL, 
                json={"model": MODEL, "messages": messages, "stream": False}, 
                timeout=300.0
            )
            llm_reply = res.json()["message"]["content"]
        except httpx.ReadTimeout:
            print("⚠️ Ollama timed out. Retrying with a simplified prompt...")
            continue
        
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
    ingest_spec_and_docs(["spec.md"])
    
    task = """
    Write a complete React App component in app/frontend/src/App.js.
    It must fetch CKA lessons from '/api/lessons' using fetch(), display a lesson list, 
    and render a 'Take Quiz' section without crashing on undefined maps.
    """
    agentic_loop(task, target_file="app/frontend/src/App.js")