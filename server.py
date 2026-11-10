"""
FastAPI proxy: wraps Ollama into an OpenAI-compatible /v1/chat/completions endpoint.
Used by the signal platform's internal Help and Chat tools.
"""

import httpx
import json
import os
import secrets
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Any

OLLAMA_BASE = "http://localhost:11434"
DEFAULT_MODEL = "gemma4:e2b"

# Set LLM_API_KEY env var on both the ThinkCentre and Railway.
# If unset, auth is disabled (fine for local-only use).
API_KEY = os.environ.get("LLM_API_KEY", "")

app = FastAPI(title="Private LLM Proxy", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not API_KEY:
        return  # auth disabled
    if not credentials or not secrets.compare_digest(credentials.credentials, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
        return {"status": "ok", "ollama": "up", "models": models}
    except Exception:
        return JSONResponse({"status": "degraded", "ollama": "down"}, status_code=503)


# ── OpenAI-compatible chat completions ───────────────────────────────────────

@app.post("/v1/chat/completions", dependencies=[Depends(require_auth)])
async def chat_completions(request: Request):
    body = await request.json()
    model = body.get("model", DEFAULT_MODEL)
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    temperature = body.get("temperature", 0.7)
    max_tokens = body.get("max_tokens", 1024)

    ollama_payload = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "think": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    if stream:
        return StreamingResponse(
            _stream_ollama(ollama_payload),
            media_type="text/event-stream",
        )

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            r = await client.post(f"{OLLAMA_BASE}/api/chat", json=ollama_payload)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Ollama error: {e}")

    data = r.json()
    content = data.get("message", {}).get("content", "")
    prompt_tokens = data.get("prompt_eval_count", 0)
    completion_tokens = data.get("eval_count", 0)

    return {
        "id": "chatcmpl-local",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


async def _stream_ollama(payload: dict):
    """Yield SSE chunks in OpenAI streaming format."""
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", f"{OLLAMA_BASE}/api/chat", json=payload) as r:
            async for line in r.aiter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue

                delta_content = chunk.get("message", {}).get("content", "")
                done = chunk.get("done", False)

                sse_chunk = {
                    "id": "chatcmpl-local",
                    "object": "chat.completion.chunk",
                    "model": payload["model"],
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": delta_content} if delta_content else {},
                            "finish_reason": "stop" if done else None,
                        }
                    ],
                }
                yield f"data: {json.dumps(sse_chunk)}\n\n"
                if done:
                    yield "data: [DONE]\n\n"


# ── Simple chat endpoint (non-OpenAI, easier to call from internal tools) ────

class ChatRequest(BaseModel):
    message: str
    system: str = "You are a helpful assistant for a trading signal platform."
    model: str = DEFAULT_MODEL
    history: list[dict[str, Any]] = []

@app.post("/chat", dependencies=[Depends(require_auth)])
async def simple_chat(req: ChatRequest):
    messages = [{"role": "system", "content": req.system}]
    messages.extend(req.history)
    messages.append({"role": "user", "content": req.message})

    payload = {
        "model": req.model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": 0.7, "num_predict": 1024},
    }

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            r = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Ollama error: {e}")

    content = r.json().get("message", {}).get("content", "")
    return {"reply": content}


# ── Help endpoint (context-aware, system-prompted for your platform) ──────────

HELP_SYSTEM = """You are the Help Assistant for Signal by Minnal, a GEO (Generative Engine Optimization) / AI-visibility tracker. You help users understand and use the product.

You can answer questions about:
- Their AI visibility score and how it's calculated
- Presence, AI-access, and extractability audits
- Prompt Coverage and the "What changed" impact tracker
- Setting up brands, tracking competitors, and reading citation gaps
- Billing, credits, and plans

Keep answers short, plain-English, and specific to Signal's features. If a question is unrelated to Signal, say so briefly rather than guessing."""

class HelpRequest(BaseModel):
    question: str
    context: str = ""  # e.g. current page name or selected signal

@app.post("/help", dependencies=[Depends(require_auth)])
async def help_endpoint(req: HelpRequest):
    system = HELP_SYSTEM
    if req.context:
        system += f"\n\nUser is currently on: {req.context}"

    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": req.question},
        ],
        "stream": False,
        "think": False,
        "options": {"temperature": 0.3, "num_predict": 200},
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            r = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Ollama error: {e}")

    return {"answer": r.json().get("message", {}).get("content", "")}
