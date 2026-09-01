from __future__ import annotations
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import engine, Base
from .routes import documents, ai, settings as settings_routes, search

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EDITOR - AI PDF Editor", version="1.0.0", description="AI-powered PDF editor built on pdf-edit-engine")

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers + rate limiting simple (in-memory)
from collections import defaultdict
import time
_rate = defaultdict(list)
@app.middleware("http")
async def rate_and_security(request: Request, call_next):
    # Rate limit: 60 req/min per IP for /api/
    if request.url.path.startswith("/api/"):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = _rate[ip]
        # prune
        window[:] = [t for t in window if now - t < 60]
        if len(window) >= 60:
            return JSONResponse({"detail": "Rate limit exceeded. Try again later."}, status_code=429)
        window.append(now)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Routers
app.include_router(documents.router)
app.include_router(ai.router)
app.include_router(settings_routes.router)
app.include_router(search.router)

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "EDITOR", "version": "1.0.0"}

@app.get("/api/operations")
def list_operations():
    from .ai_schemas import ALLOWED_OPERATIONS
    return {"operations": sorted(list(ALLOWED_OPERATIONS))}

# Serve frontend static if exists
FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"
FRONTEND_BUILD = Path(__file__).parent.parent.parent / "frontend" / ".next"  # Next.js

@app.get("/")
def root():
    return {"message": "EDITOR API is running", "docs": "/docs", "health": "/api/health"}

# Mount static files for frontend dist (Vite)
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")
    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        # Don't intercept api/docs
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        candidate = FRONTEND_DIST / full_path
        if candidate.exists() and candidate.is_file():
            return FileResponse(str(candidate))
        # fallback to index
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return JSONResponse({"detail": "Frontend not built"}, status_code=404)

# Custom error handlers
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log full error server side, return sanitized
    import traceback, logging
    logging.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    # hide stack trace from user
    return JSONResponse({"detail": "An internal error occurred. Please retry or check logs.", "error": type(exc).__name__}, status_code=500)
