from __future__ import annotations
import json
import httpx
from typing import Any

from .config import settings
from .database import SessionLocal
from .models_db import AppSettings

# Abstraction: OpenAI-compatible provider
class AIProvider:
    async def chat(self, messages: list[dict], **kwargs) -> dict:
        raise NotImplementedError
    async def test_connection(self) -> dict:
        raise NotImplementedError

class OpenAICompatibleProvider(AIProvider):
    def __init__(self, base_url: str, api_key: str, model: str, temperature: float = 0.2, max_tokens: int = 4096, extra_headers: dict | None = None):
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.extra_headers = extra_headers or {}

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        h.update(self.extra_headers)
        return h

    async def chat(self, messages: list[dict], **kwargs) -> dict:
        if not self.base_url:
            raise ValueError("AI Base URL not configured")
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "response_format": {"type": "json_object"},
        }
        timeout = kwargs.get("timeout", 30)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=self._headers(), json=payload)
            resp.raise_for_status()
            return resp.json()

    async def test_connection(self) -> dict:
        try:
            data = await self.chat([{"role": "user", "content": "Respond with: EDITOR CONNECTION OK"}], max_tokens=20, temperature=0)
            # Extract
            choices = data.get("choices", [])
            text = ""
            if choices:
                text = choices[0].get("message", {}).get("content", "")
            return {"ok": True, "response": text, "raw": data}
        except httpx.HTTPStatusError as e:
            body = e.response.text[:1000] if e.response is not None else ""
            code = e.response.status_code if e.response is not None else 0
            # Map common errors
            if code == 401:
                return {"ok": False, "error": "Invalid API key", "detail": body}
            if code == 404:
                return {"ok": False, "error": "Model not found or invalid base URL", "detail": body}
            if code == 429:
                return {"ok": False, "error": "Rate limit", "detail": body}
            return {"ok": False, "error": f"Provider error {code}", "detail": body}
        except httpx.TimeoutException:
            return {"ok": False, "error": "Timeout", "detail": "Request timed out"}
        except Exception as e:
            return {"ok": False, "error": "Provider unavailable", "detail": str(e)[:500]}

def get_configured_provider(db=None) -> OpenAICompatibleProvider:
    """Load provider config from DB (AppSettings) with fallback to env settings."""
    base_url = settings.AI_BASE_URL
    api_key = settings.AI_API_KEY
    model = settings.AI_MODEL
    temp = settings.AI_TEMPERATURE
    max_tokens = settings.AI_MAX_TOKENS
    extra_headers: dict = {}
    # Try DB override
    try:
        close = False
        if db is None:
            db = SessionLocal()
            close = True
        rows = {r.key: r.value for r in db.query(AppSettings).all()} if db else {}
        if "AI_BASE_URL" in rows and rows["AI_BASE_URL"]:
            base_url = rows["AI_BASE_URL"]
        if "AI_API_KEY" in rows and rows["AI_API_KEY"]:
            api_key = rows["AI_API_KEY"]
        if "AI_MODEL" in rows and rows["AI_MODEL"]:
            model = rows["AI_MODEL"]
        if "AI_TEMPERATURE" in rows:
            try: temp = float(rows["AI_TEMPERATURE"])
            except: pass
        if "AI_MAX_TOKENS" in rows:
            try: max_tokens = int(rows["AI_MAX_TOKENS"])
            except: pass
        if "AI_EXTRA_HEADERS" in rows and rows["AI_EXTRA_HEADERS"]:
            try: extra_headers = json.loads(rows["AI_EXTRA_HEADERS"])
            except: pass
        if close:
            db.close()
    except Exception:
        pass
    return OpenAICompatibleProvider(base_url, api_key, model, temp, max_tokens, extra_headers)

SYSTEM_PROMPT = """You are EDITOR AI, a PDF editing assistant. You MUST return ONLY valid JSON with this schema:
{
  "intent": "string - e.g. replace_text, find_text, highlight_text, etc.",
  "confidence": 0.0-1.0,
  "explanation": "short explanation",
  "operations": [
    {"type": "replace_text|replace_all|find_text|delete_text|insert_text|highlight_text|add_annotation|redact_region|extract_text|extract_table|summarize_document|rotate_page|delete_page|duplicate_page|reorder_pages|split_pdf|merge_pdf", "find": "OLD", "replace": "NEW", "scope": "document|page|selected", "page": 0, "pages": [0], "bbox": [x1,y1,x2,y2], "text": "...", "angle": 90, "order": [1,0]}
  ],
  "requires_confirmation": true
}
Rules:
- Never output code, only JSON.
- Use only allowed operation types.
- For "Replace ABC with XYZ" -> type replace_all, find ABC replace XYZ scope document.
- For highlighting -> highlight_text + bbox if provided, else without.
- Confidence should reflect certainty.
- requires_confirmation true for destructive ops.
ALWAYS return JSON object only, no markdown.
"""

def build_ai_messages(user_prompt: str, document_context: str = "", selected_text: str = "", page_context: str = "") -> list[dict]:
    ctx_parts = []
    if selected_text:
        ctx_parts.append(f"Selected text: {selected_text[:4000]}")
    if page_context:
        ctx_parts.append(f"Current page text: {page_context[:6000]}")
    if document_context:
        ctx_parts.append(f"Document excerpt: {document_context[:8000]}")
    ctx = "\n".join(ctx_parts) if ctx_parts else "No document context."
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Document context:\n{ctx}\n\nUser request: {user_prompt}\n\nReturn JSON only."}
    ]
