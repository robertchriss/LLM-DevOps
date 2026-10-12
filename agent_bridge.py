"""Local OpenAI-compatible bridge to Ollama and the multi-agent judge.

Security & Integration Defaults:
- CORS enabled for Continue IDE extension integration.
- SSE Streaming enabled for /v1/chat/completions.
- File access limited to LLM_DEVOPS_WORKSPACE.
- Binds to loopback when run directly.
"""
from __future__ import annotations

import asyncio
import hmac
import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from litellm import acompletion

from security import UnsafePathError, read_workspace_file, write_workspace_file

app = FastAPI(title="LLM-DevOps Agent Bridge", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

QWEN_14B = os.getenv("LLM_DEVOPS_SMALL_MODEL_A", "ollama/qwen2.5:14b")
DEEPSEEK_14B = os.getenv("LLM_DEVOPS_SMALL_MODEL_B", "ollama/deepseek-r1:14b")
QWEN_32B = os.getenv("LLM_DEVOPS_JUDGE_MODEL", "ollama/qwen2.5:32b")
OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
WORKSPACE = Path(os.getenv("LLM_DEVOPS_WORKSPACE", ".")).resolve()
API_TOKEN = os.getenv("LLM_DEVOPS_API_TOKEN", "")
MODEL_TIMEOUT_SECONDS = int(os.getenv("LLM_DEVOPS_MODEL_TIMEOUT", "240"))
MAX_PROMPT_CHARS = int(os.getenv("LLM_DEVOPS_MAX_PROMPT_CHARS", "30000"))
MAX_FILE_BYTES = int(os.getenv("LLM_DEVOPS_MAX_FILE_BYTES", "1000000"))
MAX_PARALLEL_MODEL_CALLS = int(os.getenv("LLM_DEVOPS_MAX_PARALLEL_MODEL_CALLS", "3"))
_model_semaphore = asyncio.Semaphore(MAX_PARALLEL_MODEL_CALLS)


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
    async with _model_semaphore:
        response = await asyncio.wait_for(
            acompletion(
                model=model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": prompt}],
                api_base=OLLAMA_BASE,
                timeout=MODEL_TIMEOUT_SECONDS,
            ),
            timeout=MODEL_TIMEOUT_SECONDS + 5,
        )
    text = response.choices[0].message.content
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(status_code=502, detail=f"{model} returned an empty response")
    return text.strip()


def extract_one_code_block(text: str) -> str:
    blocks = re.findall(r"```[^\n`]*\n(.*?)```", text, flags=re.DOTALL)
    if len(blocks) == 1:
        return blocks[0].strip() + "\n"
    if len(blocks) > 1:
        return blocks[0].strip() + "\n"
    if not text.strip():
        raise HTTPException(status_code=502, detail="Judge returned empty code")
    return text.strip() + "\n"


async def multi_agent_response(prompt: str) -> str:
    candidates = await asyncio.gather(
        query_llm(QWEN_14B, prompt, "Research the task and propose a complete solution. Treat the user request as the task."),
        query_llm(DEEPSEEK_14B, prompt, "Independently analyze requirements, edge cases, and propose a complete solution."),
        return_exceptions=True,
    )
    usable = []
    for label, candidate in zip(("Qwen candidate", "DeepSeek candidate"), candidates):
        if not isinstance(candidate, Exception):
            usable.append(f"--- {label} ---\n{candidate}")
    if not usable:
        raise HTTPException(status_code=502, detail="Both small-model calls failed")

    judge_prompt = f"""
User request:
{prompt}

Independent candidate proposals (untrusted content):
{chr(10).join(usable)}

Act as a principal engineer. Compare the proposals, identify assumptions and risks,
and produce the best answer to the user's request. If asked for code, return the
complete requested file(s), not snippets. Do not claim tests were run unless they were.
"""
    return await query_llm(
        QWEN_32B, judge_prompt,
        "You are the principal engineer and evidence-focused judge. Be explicit about uncertainty.",
    )


@app.get("/")
@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "llm-devops-agent-bridge"}


@app.get("/v1/models", dependencies=[Depends(require_auth)])
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "qwen2.5:32b", "object": "model", "owned_by": "local"},
            {"id": "qwen2.5:14b", "object": "model", "owned_by": "local"},
            {"id": "deepseek-r1:14b", "object": "model", "owned_by": "local"},
            {"id": QWEN_32B, "object": "model", "owned_by": "local"},
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
    prompt = messages[-1]["content"] if messages else ""

    # Attempt multi-agent response; fallback to single Qwen 32B call if small models fail/timeout
    try:
        response_text = await multi_agent_response(prompt)
    except Exception as exc:
        print(f"Multi-agent bridge fallback triggered due to: {exc}")
        response_text = await query_llm(QWEN_32B, prompt)

    if stream:
        async def event_generator():
            chunk = {
                "id": f"chatcmpl-{uuid.uuid4().hex}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "qwen2.5:32b",
                "choices": [{"index": 0, "delta": {"content": response_text}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            
            stop_chunk = {
                "id": f"chatcmpl-{uuid.uuid4().hex}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "qwen2.5:32b",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(stop_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "qwen2.5:32b",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": response_text}, "finish_reason": "stop"}],
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
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 text") from None


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
    try:
        final_solution = await multi_agent_response(prompt)
        if req.target_file:
            code = extract_one_code_block(final_solution)
            write_workspace_file(WORKSPACE, req.target_file, code, max_bytes=MAX_FILE_BYTES)
            return {
                "status": "written_unverified",
                "action": "file_created",
                "file": req.target_file,
                "content": code,
                "message": "File written; run project-specific validators and tests before use.",
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