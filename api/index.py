"""
Vercel Serverless entrypoint for EDITOR backend.
Vercel Python runtime expects an ASGI `app` export from api/index.py
This wraps backend/app/main.py with serverless-safe settings.

Fixes for 500 FUNCTION_INVOCATION_FAILED:
- Uses /tmp for storage/database on Vercel's read-only filesystem
- Lazy DB init to avoid import-time crashes
- Catches missing native deps (pikepdf/qpdf) with graceful fallback
"""
import os
import sys
from pathlib import Path

# Ensure project root and backend are importable
ROOT = Path(__file__).parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

# Vercel filesystem is read-only except /tmp
if os.getenv("VERCEL") == "1":
    os.environ.setdefault("STORAGE_DIR", "/tmp/storage")
    os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/editor.db")
    # Ensure dirs exist
    Path("/tmp/storage/originals").mkdir(parents=True, exist_ok=True)
    Path("/tmp/storage/versions").mkdir(parents=True, exist_ok=True)

try:
    from app.main import app  # type: ignore
except Exception as e:
    # Fallback minimal app to surface error instead of 500 crash
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    import traceback
    app = FastAPI()

    @app.get("/api/health")
    def health():
        return {"status": "error", "detail": f"Backend failed to load: {type(e).__name__}: {e}"}

    @app.get("/api/{path:path}")
    def catch_all(path: str):
        return JSONResponse(
            {
                "error": "Backend import failed",
                "type": type(e).__name__,
                "detail": str(e)[:2000],
                "trace": traceback.format_exc()[:3000],
                "hint": "Check Vercel logs: pikepdf/qpdf native dep may need --system. Consider deploying backend on Render/Railway with Docker instead of Vercel Serverless.",
            },
            status_code=500,
        )

    @app.get("/")
    def root():
        return {"message": "EDITOR API - import failed, check /api/health", "error": str(e)[:500]}
