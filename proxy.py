from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import asyncio
import json
from orchestrator import query_model, QWEN_14B, DEEPSEEK_14B, QWEN_32B

app = FastAPI()

# Enable CORS for VS Code / Continue requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root route for basic health checks
@app.get("/")
async def root():
    return {"status": "Proxy server is running"}

# Continue inspects this endpoint to verify available models
@app.get("/v1/models")
@app.get("/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "multi-agent",
                "object": "model",
                "created": 1686935000,
                "owned_by": "local-orchestrator"
            }
        ]
    }

@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    user_message = messages[-1]["content"] if messages else "Hello"

    async def generate_response():
        # Stream initial notification
        yield "data: " + json.dumps({
            "choices": [{"delta": {"content": "🧠 *Dispatching Qwen 14B & DeepSeek R1 14B concurrently...*\n\n"}}]
        }) + "\n\n"

        # Parallel 14B reasoning
        t1 = query_model(QWEN_14B, user_message)
        t2 = query_model(DEEPSEEK_14B, user_message)
        qwen_res, deepseek_res = await asyncio.gather(t1, t2)

        yield "data: " + json.dumps({
            "choices": [{"delta": {"content": "⚖️ *Qwen 32B evaluating final response...*\n\n"}}]
        }) + "\n\n"

        # 32B Evaluation
        judge_prompt = f"""
User Request: {user_message}

--- CANDIDATE A (Qwen 14B) ---
{qwen_res}

--- CANDIDATE B (DeepSeek R1 14B) ---
{deepseek_res}

Provide the final, consolidated best answer.
"""
        final_answer = await query_model(QWEN_32B, judge_prompt)

        yield "data: " + json.dumps({
            "choices": [{"delta": {"content": final_answer}}]
        }) + "\n\n"
        
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate_response(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)