import os
import re
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from litellm import acompletion

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

QWEN_14B = "ollama/qwen2.5:14b"
DEEPSEEK_14B = "ollama/deepseek-r1:14b"
QWEN_32B = "ollama/qwen2.5:32b"
OLLAMA_BASE = "http://localhost:11434"


class CommandRequest(BaseModel):
    prompt: str
    target_file: str = None


class FileActionRequest(BaseModel):
    filepath: str
    content: str = None


def extract_code(text: str) -> str:
    match = re.search(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


async def query_llm(model: str, prompt: str, system: str = "You are an expert software engineer."):
    res = await acompletion(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        api_base=OLLAMA_BASE,
    )
    return res.choices[0].message.content


@app.get("/")
async def root():
    return {"status": "online", "message": "Agent Bridge Running"}


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "qwen2.5:32b", "object": "model", "owned_by": "local"},
            {"id": "qwen2.5:14b", "object": "model", "owned_by": "local"},
            {"id": "deepseek-r1:14b", "object": "model", "owned_by": "local"},
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    user_prompt = messages[-1]["content"] if messages else ""

    if any(k in user_prompt.lower() for k in ["create", "generate", "write"]):
        qwen_task = query_llm(QWEN_14B, user_prompt, "Write production-ready code.")
        deepseek_task = query_llm(DEEPSEEK_14B, user_prompt, "Provide architectural logic and code structure.")
        
        q_res, ds_res = await asyncio.gather(qwen_task, deepseek_task)

        judge_prompt = f"""Synthesize the optimal solution for: "{user_prompt}"
--- SOLUTION A ---
{q_res}
--- SOLUTION B ---
{ds_res}
Output ONLY executable code inside standard markdown code blocks."""

        final_res = await query_llm(QWEN_32B, judge_prompt, "You are a Principal Software Architect.")
    else:
        final_res = await query_llm(QWEN_32B, user_prompt)

    return {
        "id": "chatcmpl-agent-bridge",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "qwen2.5:32b",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": final_res},
                "finish_reason": "stop",
            }
        ],
    }


@app.post("/api/file/read")
async def read_file(req: FileActionRequest):
    try:
        with open(req.filepath, "r", encoding="utf-8") as f:
            return {"status": "success", "content": f.read()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/file/write")
async def write_file(req: FileActionRequest):
    try:
        os.makedirs(os.path.dirname(req.filepath), exist_ok=True)
        with open(req.filepath, "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"status": "success", "file": req.filepath}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/command")
async def execute_command(req: CommandRequest):
    prompt = req.prompt.strip()

    if req.target_file or prompt.lower().startswith("create ") or prompt.lower().startswith("generate "):
        qwen_task = query_llm(QWEN_14B, prompt, "Write high-performance production code.")
        deepseek_task = query_llm(DEEPSEEK_14B, prompt, "Analyze requirements and output structured code.")

        q_res, ds_res = await asyncio.gather(qwen_task, prompt)

        judge_prompt = f"""Synthesize the best solution for: "{prompt}"
--- CANDIDATE A ---
{q_res}
--- CANDIDATE B ---
{ds_res}
Output ONLY final clean code inside standard markdown code blocks."""

        final_solution = await query_llm(QWEN_32B, judge_prompt, "You are a Principal Architect.")
        clean_code = extract_code(final_solution)

        if req.target_file:
            os.makedirs(os.path.dirname(req.target_file), exist_ok=True)
            with open(req.target_file, "w", encoding="utf-8") as f:
                f.write(clean_code)
            return {"status": "success", "action": "file_created", "file": req.target_file, "content": clean_code}

        return {"status": "success", "action": "code_generated", "content": clean_code}

    response = await query_llm(QWEN_14B, prompt)
    return {"status": "success", "action": "chat", "content": response}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)