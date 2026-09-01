# EDITOR — AI PDF Editor

> Professional AI-powered PDF editing built on **[pdf-edit-engine](https://github.com/AryanBV/pdf-edit-engine)**. Format-preserving text editing at the content-stream level — original fonts, layout and spacing stay intact.

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue) ![License MIT](https://img.shields.io/badge/license-MIT-green) ![No Ollama](https://img.shields.io/badge/AI-OpenAI--compatible%20only-orange)

## Overview

EDITOR transforms `pdf-edit-engine` (pure Python engine) into a complete web application:

- **Dashboard** with stats (Total Documents, Edited PDFs, AI Operations, Recent Activity)
- **Document Library** — Grid/List, search, favorites, trash, rename/duplicate
- **PDF Viewer** — PDF.js, thumbnails, zoom, page nav, text selection
- **Toolbar** — Select, Edit Text, Find & Replace, Highlight, Comment, Redact, Draw, Undo/Redo, Rotate, Pages, AI
- **AI Assistant (right panel)** — natural-language → structured JSON → preview → apply, using **user-provided OpenAI-compatible API**
- **Version History** — Original never overwritten; every edit creates `version-N.pdf` with fidelity report; Compare (Before/After) side-by-side
- **Page Management**, **Annotations**, **Redaction**, **Search**, **Export**, **Audit Log**, **AI History**

> **Bank Statement Mode**: supported as normal PDFs — search, extraction, highlighting, highlight salary/EMI, redact account info — while preserving original and showing edited/derived version transparently.

## Architecture

```
User Prompt
  ↓
Document Context Extraction (selected text / current page / entire doc — cached, not re-sent)
  ↓
AI API (OpenAI-compatible POST /chat/completions via server-side proxy)
  ↓
Structured JSON Response { intent, confidence, explanation, operations[], requires_confirmation }
  ↓
Strict JSON Schema Validation → reject invalid / unknown ops → error + retry
  ↓
Operation Preview (find count, bbox samples)
  ↓
User Approval (Cancel / Preview / Apply)
  ↓
PDF Engine (pdf-edit-engine) via FastAPI
  ↓
FidelityReport + New Version → Compare → Download
```

**Provider abstraction** (`backend/app/ai_provider.py:OpenAICompatibleProvider`):
- `AIProvider` → `OpenAICompatibleProvider` (base_url, api_key, model, temperature, max_tokens, extra_headers)
- No hard-coded vendor. Base URL comes from DB settings or `AI_BASE_URL` env.
- Frontend `POST /api/ai/chat` → Server reads encrypted/configured credentials → calls provider → returns sanitized JSON. Key never in JS bundle.

**PDF Engine integration** (`backend/app/pdf_engine.py`):
Wraps `pdf_edit_engine.find / replace / replace_all / batch_replace / add_highlight / rotate_pages / delete_pages / reorder_pages / merge_pdfs / split_pdf / get_text / get_text_layout / add_annotation`. Every edit returns `FidelityReport` → stored per version.

**Storage**: `backend/storage/originals/` + `backend/storage/versions/` + `editor.db` (SQLite). Each document keeps `original.pdf` immutable.

## Project Structure

```
EDITOR/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI, CORS, rate-limit, mount frontend
│   │   ├── config.py            # pydantic-settings (AI_* , STORAGE, DB)
│   │   ├── database.py          # SQLAlchemy engine
│   │   ├── models_db.py         # Document, Version, AuditLog, AIHistory, AppSettings
│   │   ├── pdf_engine.py        # pdf-edit-engine wrappers
│   │   ├── ai_provider.py       # OpenAICompatibleProvider + build_ai_messages
│   │   ├── ai_schemas.py        # Operation registry + JSON schema (17 ops)
│   │   └── routes/
│   │       ├── documents.py     # upload, find, replace, highlight, annotate, redact, pages, merge/split, export
│   │       ├── ai.py            # /ai/chat, /ai/preview, /ai/apply, /ai/history, /ai/test-connection
│   │       ├── settings.py      # /settings/ai (masked key)
│   │       └── search.py        # /search, /stats, /audit
│   ├── storage/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                    # Vite + React + Tailwind + React Router + pdfjs-dist
│   ├── src/
│   │   ├── App.tsx
│   │   ├── lib/api.ts
│   │   ├── components/{Sidebar,PdfViewer,AiPanel}.tsx
│   │   └── pages/{Dashboard,Documents,Editor,Settings,AiHistory}.tsx
│   ├── vite.config.ts (proxy /api → :8000)
│   └── Dockerfile
├── .env.example
├── docker-compose.yml
└── README.md (this file)
```

## AI Configuration (User-Provided Free API)

Settings UI at `/settings/ai` (premium dashboard):

- Provider: **OpenAI Compatible** (fixed, no Ollama)
- Fields: API Base URL, API Key (masked `****abcd`), Model, Temperature, Max Tokens
- Buttons: **Save Settings** (writes to DB `AppSettings`, server-side only), **Test Connection** → `POST /chat/completions` with `"EDITOR CONNECTION OK"` → shows ✓ Connected or ✕ with `Invalid API key | Invalid base URL | Model not found | Rate limit | Timeout | Invalid response | Provider unavailable`
- Cost control: token limits, request size limits, context trimming (selective context, not whole PDF), cached text extraction, request cancellation, debounced search.

`.env` fallback (never exposed to browser):
```
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-...
AI_MODEL=gpt-4o-mini
```

**Do NOT** use `NEXT_PUBLIC_*` for keys. Frontend calls `POST /api/ai/chat` → server injects key.

## Supported AI Operations (Registry)

Controlled list — unknown ops rejected (strict schema):

`find_text | replace_text | replace_all | delete_text | insert_text | highlight_text | add_annotation | redact_region | extract_text | extract_table | summarize_document | rotate_page | delete_page | duplicate_page | reorder_pages | split_pdf | merge_pdf`

AI prompt examples handled: “Find every occurrence of ABC Limited”, “Replace ABC Limited with ABC Private Limited”, “Highlight all salary transactions”, “Redact the account number on page 2”, “Extract the table from page 4”, “Summarize this document”, etc.

Response always:

```json
{
  "intent": "replace_text",
  "confidence": 0.97,
  "explanation": "Replace the requested text.",
  "operations": [{ "type": "replace_all", "find": "OLD TEXT", "replace": "NEW TEXT", "scope": "document" }],
  "requires_confirmation": true
}
```

Validation rejects raw AI output that skips schema, never executes arbitrary code.

## Installation & Running Locally

### Prerequisites
- Python 3.12+
- Node 20+

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# copy env
cp ../.env.example ../.env  # edit AI_* if needed — or configure via UI
uvicorn app.main:app --reload --port 8000
# API at http://localhost:8000/docs  health at /api/health
```

### Frontend

```bash
cd frontend
npm install
npm run dev  # http://localhost:3000  (proxies /api to 8000)
# production build served by FastAPI if frontend/dist exists
npm run build
```

### Docker

```bash
cp .env.example .env
docker-compose up --build
# frontend http://localhost:3000  api http://localhost:8000
```

## Production Deployment

- Set `SECRET_KEY` to random 32+ chars, use Postgres `DATABASE_URL` if needed.
- Put behind HTTPS (Nginx/Cloudflare). Storage on persistent volume/S3.
- Env only on server — UI saves to DB encrypted at rest if desired.
- Enable rate limiting (included: 60 req/min/IP), audit logs, input validation (PDF magic check, 100MB limit, page index bounds), AI output validation, PDF processing isolation.

## Security

- Upload validation (PDF header, size), private storage, server-side API keys, no key in JS, rate limiting, audit logs, `X-Content-Type-Options: nosniff`, CORS, input & AI-output validation, pikepdf isolation.
- Audit trail records upload/open/edit/AI request/preview/apply/annotation/redaction/export/download with User, Action, Document, Date, Operation, Status, Version.

## API Quick Reference

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/documents/upload | Upload PDF |
| GET | /api/documents/ | List (q, favorite) |
| GET | /api/documents/{id}/file | Latest or ?version=N |
| POST | /api/documents/{id}/find | find text |
| POST | /api/documents/{id}/replace | replace (supports dry_run) |
| POST | /api/documents/{id}/highlight | add highlight |
| POST | /api/documents/{id}/annotate | add_annotation |
| POST | /api/documents/{id}/redact | redact region (preview → confirm) |
| POST | /api/documents/{id}/pages/* | rotate/delete/duplicate/reorder/insert-blank/split |
| POST | /api/documents/merge | merge multiple docs |
| POST | /api/ai/chat | structured JSON from prompt |
| POST | /api/ai/preview | compute match counts |
| POST | /api/ai/apply | apply validated ops → new versions |
| POST | /api/ai/test-connection | minimal test |
| GET | /api/ai/history | AI history |
| GET | /api/settings/ai | masked settings |
| POST | /api/settings/ai | save settings (server-side) |
| GET | /api/search | global search |
| GET | /api/stats | dashboard stats |
| GET | /api/audit | audit logs |
| GET | /api/operations | allowed ops |

## Final Workflow (as specified)

```
USER UPLOADS PDF → EDITOR OPENS PDF → USER TYPES: "Find all occurrences of XYZ."
→ AI API → STRUCTURED JSON → VALIDATE → SHOW RESULTS → USER: "Replace them with ABC."
→ AI API → STRUCTURED OPERATION → PREVIEW → USER CLICKS APPLY → PDF ENGINE → FIDELITY CHECK → VERSION CREATED → USER CAN DOWNLOAD
```

## Testing

Manual checks (see `backend/app/routes/*`):
1. Upload 2. Open 3. Search 4. Edit text 5. Find/replace 6. Annotation 7. Redaction 8. Page ops 9. AI connection 10. AI prompt 11. Structured JSON 12. Preview 13. Apply 14. Version 15. Compare 16. Export 17. Audit log
Plus AI failure cases: invalid key, invalid URL, unavailable model, timeout, rate limit, malformed JSON, provider error — all recover gracefully with polished errors (no stack traces).

## No Ollama

This project **does not** install, configure, mention (beyond this line) or depend on local LLM servers. The only AI mechanism is user-configured OpenAI-compatible API.

## License

MIT — pdf-edit-engine core retains its MIT license.
