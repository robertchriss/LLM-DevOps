"""Local OpenAI-compatible bridge to Ollama and agent router."""
from __future__ import annotations

import asyncio
import hmac
import json
import os
import re
import time
import uuid
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from security import UnsafePathError, read_workspace_file, write_workspace_file, resolve_safe_path

app = FastAPI(title="LLM-DevOps Agent Bridge", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

QWEN_14B = os.getenv("LLM_DEVOPS_SMALL_MODEL_A", "qwen2.5:14b")
QWEN_32B = os.getenv("LLM_DEVOPS_JUDGE_MODEL", "qwen2.5:32b")
OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
WORKSPACE = Path(os.getenv("LLM_DEVOPS_WORKSPACE", ".")).resolve()
API_TOKEN = os.getenv("LLM_DEVOPS_API_TOKEN", "")
MODEL_TIMEOUT_SECONDS = float(os.getenv("LLM_DEVOPS_MODEL_TIMEOUT", "240"))
MAX_PROMPT_CHARS = int(os.getenv("LLM_DEVOPS_MAX_PROMPT_CHARS", "30000"))
MAX_FILE_BYTES = int(os.getenv("LLM_DEVOPS_MAX_FILE_BYTES", "1000000"))


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CommandRequest(StrictRequest):
    prompt: str = Field(min_length=1, max_length=MAX_PROMPT_CHARS)
    target_file: str | None = Field(default=None, max_length=500)


class FileActionRequest(StrictRequest):
    filepath: str = Field(min_length=1, max_length=500)
    content: str | None = Field(default=None, max_length=MAX_FILE_BYTES)


async def require_auth(authorization: str | None = Header(default=None)) -> None:
    if not API_TOKEN:
        return
    expected = f"Bearer {API_TOKEN}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


async def query_llm(
    model: str,
    prompt: str,
    system: str = "You are a careful software engineering assistant.",
) -> str:
    """Query Ollama REST API directly via HTTPX."""
    clean_model = model.replace("ollama/", "")
    url = f"{OLLAMA_BASE}/api/chat"
    
    payload = {
        "model": clean_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }

    try:
        async with httpx.AsyncClient(timeout=MODEL_TIMEOUT_SECONDS) as client:
            res = await client.post(url, json=payload)
            if res.status_code != 200:
                print(f"Ollama error status {res.status_code}: {res.text}")
                raise HTTPException(status_code=502, detail=f"Ollama model '{clean_model}' returned {res.status_code}")
            
            data = res.json()
            content = data.get("message", {}).get("content", "")
            if not content.strip():
                raise HTTPException(status_code=502, detail=f"Model '{clean_model}' returned an empty response")
            return content.strip()
            
    except httpx.RequestError as exc:
        print(f"Failed to connect to Ollama at {url}: {exc}")
        raise HTTPException(status_code=502, detail=f"Failed to connect to Ollama: {exc}") from exc


def extract_one_code_block(text: str) -> str:
    blocks = re.findall(r"```[^\n`]*\n(.*?)```", text, flags=re.DOTALL)
    if len(blocks) >= 1:
        return blocks[0].strip() + "\n"
    if not text.strip():
        raise HTTPException(status_code=502, detail="LLM returned empty code")
    return text.strip() + "\n"


async def route_llm_request(prompt: str) -> str:
    """Dynamically route to Fast or Heavy model based on task complexity."""
    
    classifier_prompt = f"""
    Evaluate the complexity of this user request:
    "{prompt}"
    
    RULES:
    - If the request is a simple question, a minor bug fix, or a single-file edit, reply with exactly the word: FAST
    - If the request asks to "build an app", generate multi-tier architecture, create new infrastructure, or write complex multi-file logic, reply with exactly the word: HEAVY
    
    Respond ONLY with FAST or HEAVY. No other text.
    """
    
    try:
        # Step 1: Use 14B to instantly classify the intent
        print("Classifying task complexity...")
        decision = await query_llm(QWEN_14B, classifier_prompt, "You are a strict task routing system.")
        
        # Step 2: Route based on the decision
        if "HEAVY" in decision.upper():
            print(f"Task is HEAVY. Routing to Architect Model ({QWEN_32B})...")
            return await query_llm(QWEN_32B, prompt)
        else:
            print(f"Task is FAST. Routing to Code Model ({QWEN_14B})...")
            return await query_llm(QWEN_14B, prompt)
            
    except Exception as exc:
        print(f"Routing failed or model crashed: {exc}. Falling back to safe {QWEN_32B} execution...")
        return await query_llm(QWEN_32B, prompt)


@app.get("/")
@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "llm-devops-agent-bridge"}


@app.get("/v1/models", dependencies=[Depends(require_auth)])
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "qwen2.5:14b", "object": "model", "owned_by": "local"},
            {"id": "qwen2.5:32b", "object": "model", "owned_by": "local"},
        ],
    }


@app.post("/v1/chat/completions", dependencies=[Depends(require_auth)])
async def chat_completions(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Request body must be valid JSON") from None
    
    messages = data.get("messages", [])
    stream = data.get("stream", False)
    if not isinstance(messages, list) or not messages:
        raise HTTPException(status_code=400, detail="messages must be a non-empty list")
    
    last = messages[-1]
    if not isinstance(last, dict) or not isinstance(last.get("content"), str):
        raise HTTPException(status_code=400, detail="Last message must contain string content")
    
    prompt = last["content"]
    if not prompt.strip() or len(prompt) > MAX_PROMPT_CHARS:
        raise HTTPException(status_code=400, detail="Prompt is empty or exceeds configured limit")

    response_text = await route_llm_request(prompt)

    if stream:
        async def event_generator():
            chunk = {
                "id": f"chatcmpl-{uuid.uuid4().hex}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "qwen2.5:14b",
                "choices": [{"index": 0, "delta": {"content": response_text}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            
            stop_chunk = {
                "id": f"chatcmpl-{uuid.uuid4().hex}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "qwen2.5:14b",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(stop_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "qwen2.5:14b",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": response_text},
            "finish_reason": "stop",
        }],
    }


@app.post("/api/file/read", dependencies=[Depends(require_auth)])
async def read_file(req: FileActionRequest):
    try:
        return {
            "status": "success",
            "file": req.filepath,
            "content": read_workspace_file(WORKSPACE, req.filepath, max_bytes=MAX_FILE_BYTES),
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found") from None
    except (UnsafePathError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@app.post("/api/file/write", dependencies=[Depends(require_auth)])
async def write_file(req: FileActionRequest):
    if req.content is None:
        raise HTTPException(status_code=400, detail="content is required")
    try:
        write_workspace_file(WORKSPACE, req.filepath, req.content, max_bytes=MAX_FILE_BYTES)
        return {"status": "success", "file": req.filepath}
    except (UnsafePathError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@app.post("/api/command", dependencies=[Depends(require_auth)])
async def execute_command(req: CommandRequest):
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt cannot be empty")
    
    # Validate target path FIRST before triggering LLM calls
    if req.target_file:
        try:
            resolve_safe_path(WORKSPACE, req.target_file)
        except (UnsafePathError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None

    try:
        final_solution = await route_llm_request(prompt)
        if req.target_file:
            code = extract_one_code_block(final_solution)
            write_workspace_file(WORKSPACE, req.target_file, code, max_bytes=MAX_FILE_BYTES)
            return {
                "status": "written_unverified",
                "action": "file_created",
                "file": req.target_file,
                "content": code,
                "message": "File written successfully.",
            }
        return {"status": "success", "action": "answer", "content": final_solution}
    except HTTPException:
        raise
    except (UnsafePathError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Orchestration failed: {exc}") from exc


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("LLM_DEVOPS_BRIDGE_PORT", "8000")))