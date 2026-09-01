"""
Vercel Serverless - LIGHTWEIGHT stub to avoid pikepdf native crash.

Vercel's Python runtime cannot build pikepdf (needs libqpdf-dev) ->
FUNCTION_INVOCATION_FAILED at pip install time.
So this stub has ZERO heavy native deps and always boots.
It proxy-passes to full backend if you deploy backend on Render/Railway,
otherwise returns helpful JSON.

Deploy options:
1) Recommended: Frontend on Vercel, Backend on Render (Docker) -> set BACKEND_URL env
2) All on Vercel: will return 503 for PDF ops (native dep unavailable) but /api/health works
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

BACKEND_URL = os.getenv("BACKEND_URL", "").rstrip("/")

app = FastAPI(title="EDITOR - AI PDF Editor (Vercel Stub)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    # Always 200 - proves function booted, isolates build vs runtime crash
    return {
        "status": "ok",
        "service": "EDITOR",
        "mode": "vercel-stub",
        "backend_url": BACKEND_URL or "not set",
        "hint": "If BACKEND_URL is set, /api/* will proxy to Render backend. Otherwise PDF ops are stubbed because pikepdf cannot run on Vercel serverless.",
    }

@app.get("/api/operations")
def ops():
    return {"operations": ["find_text","replace_text","replace_all","delete_text","highlight_text","add_annotation","redact_region","extract_text","extract_table","summarize_document","rotate_page","delete_page","duplicate_page","reorder_pages","split_pdf","merge_pdf"], "note": "stub - full engine on Docker backend"}

@app.api_route("/api/{path:path}", methods=["GET","POST","PUT","DELETE","PATCH","OPTIONS"])
async def proxy(path: str, request: Request):
    # If BACKEND_URL configured, proxy to real backend (Render/Railway)
    if BACKEND_URL:
        import httpx
        url = f"{BACKEND_URL}/api/{path}"
        # forward query
        if request.url.query:
            url += f"?{request.url.query}"
        body = await request.body()
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host","content-length")}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.request(request.method, url, content=body, headers=headers)
                return JSONResponse(content=resp.json() if resp.headers.get("content-type","").startswith("application/json") else {"raw": resp.text[:5000]}, status_code=resp.status_code)
        except Exception as e:
            return JSONResponse({"error": "Proxy to backend failed", "backend_url": BACKEND_URL, "detail": str(e)[:1000], "hint": "Check BACKEND_URL and that Render backend is running"}, status_code=502)
    # No backend -> stub response explaining Vercel limitation
    return JSONResponse(
        {
            "error": "PDF engine unavailable on Vercel serverless",
            "detail": f"POST /api/{path} requires pikepdf/qpdf which cannot build on Vercel Python runtime. This stub always boots (200 on /api/health) to avoid FUNCTION_INVOCATION_FAILED.",
            "fix": "Deploy backend/ via Docker on Render (free): https://render.com -> New Web Service -> connect repo, Root Directory=backend, Dockerfile, set env AI_*; then set Vercel env BACKEND_URL=https://your-render-backend.onrender.com",
            "alternative": "Or deploy all via Docker: use opencode.json services on a Docker platform, not Vercel serverless",
            "requested_path": f"/api/{path}",
        },
        status_code=503,
    )

@app.get("/")
def root():
    return {"message": "EDITOR API (Vercel stub) running", "health": "/api/health", "docs_hint": "Full docs at Render backend /docs if BACKEND_URL set"}
