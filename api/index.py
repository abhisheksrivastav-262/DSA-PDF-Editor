"""
Vercel Serverless - ZERO-DEPS stub (no FastAPI/pydantic, no Rust build)
Fixes: PyO3 0.24.1 max Python 3.13, but Vercel default is 3.14 -> pydantic-core fails.
Using stdlib only: no pip build, boots on any Python.
"""
import os
import json
from http.server import BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BACKEND_URL = os.getenv("BACKEND_URL", "").rstrip("/")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.handle_request("GET")
    def do_POST(self):
        self.handle_request("POST")
    def do_PUT(self):
        self.handle_request("PUT")
    def do_DELETE(self):
        self.handle_request("DELETE")
    def do_PATCH(self):
        self.handle_request("PATCH")
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,PATCH,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
        self.end_headers()

    def handle_request(self, method):
        path = self.path.split("?")[0]
        query = self.path.split("?")[1] if "?" in self.path else ""

        # CORS
        cors_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,PATCH,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        }

        # Proxy to Render backend if configured
        if BACKEND_URL and path.startswith("/api/"):
            try:
                url = f"{BACKEND_URL}{self.path}"
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length > 0 else None
                req = Request(url, data=body, method=method)
                for k, v in self.headers.items():
                    if k.lower() not in ("host", "content-length"):
                        req.add_header(k, v)
                with urlopen(req, timeout=30) as resp:
                    data = resp.read()
                    self.send_response(resp.status)
                    for hk, hv in cors_headers.items():
                        self.send_header(hk, hv)
                    for hk, hv in resp.headers.items():
                        if hk.lower() not in ("content-length", "content-encoding"):
                            self.send_header(hk, hv)
                    self.end_headers()
                    self.wfile.write(data)
                    return
            except HTTPError as e:
                data = e.read()
                self.send_response(e.code)
                for hk, hv in cors_headers.items():
                    self.send_header(hk, hv)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception as e:
                self.send_response(502)
                for hk, hv in cors_headers.items():
                    self.send_header(hk, hv)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Proxy failed", "backend_url": BACKEND_URL, "detail": str(e)[:1000]}).encode())
                return

        # Stub responses
        self.send_response(200)
        for hk, hv in cors_headers.items():
            self.send_header(hk, hv)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        if path in ("/api/health", "/api/operations", "/api/health/"):
            body = {"status": "ok", "service": "EDITOR", "mode": "vercel-stub-pure-stdlib", "backend_url": BACKEND_URL or "not set", "path": path, "hint": "No FastAPI/pydantic - boots on Python 3.14. Set BACKEND_URL to Render backend for full PDF ops."}
        elif path.startswith("/api/"):
            body = {"error": "PDF engine unavailable on Vercel serverless (pure stub)", "requested_path": path, "fix": "Deploy backend/ via Docker on Render (free) -> Set Vercel env BACKEND_URL=https://your-render.onrender.com", "detail": "This stub has zero native deps to avoid PyO3 3.14 crash."}
        elif path in ("/", "/docs", "/openapi.json"):
            body = {"message": "EDITOR API (Vercel pure-stdlib stub) running", "health": "/api/health", "path": path}
        else:
            body = {"status": "ok", "path": path}
        self.wfile.write(json.dumps(body).encode())
