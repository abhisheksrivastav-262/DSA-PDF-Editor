from __future__ import annotations
import json, re, tempfile, shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models_db import Document, Version, AIHistory, AuditLog
from ..config import settings
from ..ai_provider import get_configured_provider, build_ai_messages, SYSTEM_PROMPT
from ..ai_schemas import AIResponse, ALLOWED_OPERATIONS
from ..pdf_engine import pdf_text_preview, pdf_find, pdf_replace, pdf_highlight, pdf_rotate, pdf_delete_pages, pdf_reorder, pdf_merge

router = APIRouter(prefix="/api/ai", tags=["ai"])

def audit(db: Session, doc_id, action, detail=""):
    try:
        db.add(AuditLog(document_id=doc_id, action=action, detail=detail))
        db.commit()
    except Exception:
        pass

def validate_ai_response(data: dict) -> dict:
    # strict validation
    if not isinstance(data, dict):
        raise ValueError("AI response must be JSON object")
    for k in ["intent", "confidence", "explanation", "operations", "requires_confirmation"]:
        if k not in data:
            raise ValueError(f"Missing key: {k}")
    if not isinstance(data["operations"], list):
        raise ValueError("operations must be list")
    for op in data["operations"]:
        if "type" not in op:
            raise ValueError("operation missing type")
        if op["type"] not in ALLOWED_OPERATIONS:
            raise ValueError(f"Unknown operation: {op['type']}")
    # confidence range
    if not (0 <= float(data["confidence"]) <= 1):
        raise ValueError("confidence out of range")
    return data

@router.post("/chat")
async def ai_chat(payload: dict, db: Session = Depends(get_db)):
    prompt: str = payload.get("prompt") or payload.get("message") or ""
    doc_id: int | None = payload.get("document_id") or payload.get("documentId")
    context_selector: str = payload.get("context") or "current_page"  # selected_text, current_page, selected_pages, entire_document
    selected_text: str = payload.get("selected_text") or ""
    page_text: str = payload.get("page_text") or ""
    if not prompt:
        raise HTTPException(400, "prompt required")
    document_context = ""
    if doc_id:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            v = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first()
            path = v.file_path if v else doc.original_path
            # limit context based on selector
            if context_selector == "entire_document":
                document_context = pdf_text_preview(path, 12000)
            elif context_selector == "current_page":
                document_context = page_text[:6000] if page_text else pdf_text_preview(path, 6000)
            elif context_selector == "selected_text":
                document_context = selected_text[:4000] if selected_text else pdf_text_preview(path, 4000)
            else:
                document_context = pdf_text_preview(path, 6000)
    provider = get_configured_provider(db)
    if not provider.base_url or not provider.model:
        # No provider configured -> return mock operation for demo
        # Create mock structured response based on prompt heuristics
        mock = heuristic_mock(prompt)
        # store history
        hist = AIHistory(document_id=doc_id, prompt=prompt, model=provider.model or "mock", provider_url=provider.base_url or "mock", operation=mock["intent"], status="preview", response_json=mock)
        db.add(hist)
        db.commit()
        audit(db, doc_id, "AI request", f"Mock: {prompt[:100]}")
        return {"mock": True, "response": mock, "warning": "AI provider not configured - showing heuristic preview. Configure AI settings to use real model."}
    messages = build_ai_messages(prompt, document_context, selected_text, page_text)
    try:
        raw = await provider.chat(messages)
        content = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        # try parse JSON
        # strip markdown fences
        content_clean = re.sub(r"^```(?:json)?\s*", "", content.strip())
        content_clean = re.sub(r"\s*```$", "", content_clean.strip())
        try:
            parsed = json.loads(content_clean)
        except Exception as e:
            raise HTTPException(502, f"AI returned invalid JSON: {e}. Raw: {content[:500]}")
        validated = validate_ai_response(parsed)
        # store history
        hist = AIHistory(document_id=doc_id, prompt=prompt, model=provider.model, provider_url=provider.base_url, operation=validated["intent"], status="preview", response_json=validated)
        db.add(hist)
        db.commit()
        audit(db, doc_id, "AI request", f"{prompt[:80]} -> {validated['intent']}")
        return {"response": validated, "raw": content}
    except HTTPException:
        raise
    except Exception as e:
        # store failed history
        try:
            hist = AIHistory(document_id=doc_id, prompt=prompt, model=provider.model, provider_url=provider.base_url, operation="error", status="failed", response_json={"error": str(e)[:500]})
            db.add(hist)
            db.commit()
        except: pass
        raise HTTPException(502, f"AI provider error: {type(e).__name__}: {e}")

def heuristic_mock(prompt: str) -> dict:
    pl = prompt.lower()
    if "replace" in pl and "with" in pl:
        # try extract find/replace
        m = re.search(r"replace\s+[\"']?(.+?)[\"']?\s+with\s+[\"']?(.+?)[\"']?[\.\"]?$", prompt, re.I)
        if m:
            find, repl = m.group(1).strip(), m.group(2).strip()
        else:
            # fallback
            find, repl = "ABC Limited", "ABC Private Limited"
        return {"intent": "replace_text", "confidence": 0.85, "explanation": f"Replace '{find}' with '{repl}'", "operations": [{"type": "replace_all", "find": find, "replace": repl, "scope": "document"}], "requires_confirmation": True}
    if "find" in pl or "search" in pl:
        m = re.search(r"find\s+(?:all\s+)?(?:occurrences\s+of\s+)?[\"']?(.+?)[\"']?[\.\"]?$", prompt, re.I)
        find = m.group(1).strip() if m else "ABC Limited"
        return {"intent": "find_text", "confidence": 0.9, "explanation": f"Find all occurrences of {find}", "operations": [{"type": "find_text", "find": find, "scope": "document"}], "requires_confirmation": False}
    if "highlight" in pl:
        return {"intent": "highlight_text", "confidence": 0.88, "explanation": "Highlight matched transactions", "operations": [{"type": "highlight_text", "find": "salary", "scope": "document"}], "requires_confirmation": True}
    if "highlight" in pl or "annotate" in pl:
        return {"intent": "highlight_text", "confidence": 0.8, "explanation": "Highlight request", "operations": [{"type": "highlight_text", "scope": "document"}], "requires_confirmation": True}
    if "redact" in pl:
        return {"intent": "redact_region", "confidence": 0.82, "explanation": "Redact sensitive region", "operations": [{"type": "redact_region", "bbox": [100,500,300,520], "page": 0}], "requires_confirmation": True}
    if "summarize" in pl:
        return {"intent": "summarize_document", "confidence": 0.95, "explanation": "Summarize document", "operations": [{"type": "summarize_document", "scope": "document"}], "requires_confirmation": False}
    if "extract" in pl and "table" in pl:
        return {"intent": "extract_table", "confidence": 0.9, "explanation": "Extract table", "operations": [{"type": "extract_table", "page": 0}], "requires_confirmation": False}
    return {"intent": "find_text", "confidence": 0.6, "explanation": "Generic find operation", "operations": [{"type": "find_text", "find": prompt[:50], "scope": "document"}], "requires_confirmation": False}

@router.post("/preview")
async def ai_preview(payload: dict, db: Session = Depends(get_db)):
    # Validate and show what operation would do (without applying)
    doc_id = payload.get("document_id")
    ai_response = payload.get("ai_response") or payload.get("operations")
    # ai_response may be the validated JSON
    if isinstance(ai_response, dict) and "operations" in ai_response:
        ops = ai_response["operations"]
    elif isinstance(ai_response, list):
        ops = ai_response
    else:
        raise HTTPException(400, "ai_response with operations required")
    # For each operation, compute preview (e.g., find counts)
    previews = []
    if doc_id:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        v = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first() if doc else None
        path = v.file_path if v else (doc.original_path if doc else None)
        for op in ops:
            t = op.get("type")
            if t in ("find_text","replace_text","replace_all"):
                find = op.get("find") or op.get("text") or ""
                if find and path:
                    try:
                        matches = pdf_find(path, find)
                        previews.append({"type": t, "find": find, "replace": op.get("replace"), "matches": len(matches), "sample_boxes": [m.bounding_box for m in matches[:3]]})
                    except Exception as e:
                        previews.append({"type": t, "error": str(e)[:300]})
                else:
                    previews.append({"type": t, "find": find, "matches": "unknown"})
            elif t == "highlight_text":
                previews.append({"type": t, "detail": "Will highlight matching regions", "operation": op})
            else:
                previews.append({"type": t, "operation": op, "detail": "Preview available"})
    else:
        for op in ops:
            previews.append({"type": op.get("type"), "operation": op})
    audit(db, doc_id, "AI preview", f"{len(previews)} ops")
    return {"previews": previews}

@router.post("/apply")
async def ai_apply(payload: dict, db: Session = Depends(get_db)):
    doc_id = payload.get("document_id")
    ai_response = payload.get("ai_response")
    if not doc_id or not ai_response:
        raise HTTPException(400, "document_id and ai_response required")
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    validated = validate_ai_response(ai_response) if isinstance(ai_response, dict) and "operations" in ai_response else None
    if not validated:
        raise HTTPException(400, "Invalid ai_response")
    v = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first()
    path = v.file_path if v else doc.original_path
    results = []
    current_path = path
    # Apply operations sequentially, creating new versions
    from pathlib import Path
    from ..config import settings
    VERSIONS = Path(settings.STORAGE_DIR) / "versions"
    for op in validated["operations"]:
        t = op.get("type")
        try:
            if t in ("replace_text","replace_all"):
                find = op.get("find")
                repl = op.get("replace", "")
                new_ver = (db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first().version_number + 1)
                out_path = str(VERSIONS / f"{doc_id}_v{new_ver}.pdf")
                res = pdf_replace(current_path, find, repl, out_path, dry_run=False)
                if not res.get("success"):
                    results.append({"type": t, "success": False, "error": res.get("error")})
                    continue
                # create version entry
                fidelity = res.get("fidelity")
                version = Version(document_id=doc_id, version_number=new_ver, file_path=out_path, operation=t, detail=f"AI: {find}->{repl}", is_ai=True, fidelity_report=fidelity)
                db.add(version)
                db.commit()
                current_path = out_path
                doc.current_version = new_ver
                db.commit()
                results.append({"type": t, "success": True, "version": new_ver, "fidelity": fidelity, "matches": res.get("matches")})
            elif t == "delete_text":
                find = op.get("find")
                new_ver = (db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first().version_number + 1)
                out_path = str(VERSIONS / f"{doc_id}_v{new_ver}.pdf")
                res = pdf_replace(current_path, find, "", out_path, dry_run=False)
                if res.get("success"):
                    version = Version(document_id=doc_id, version_number=new_ver, file_path=out_path, operation=t, detail=f"AI delete {find}", is_ai=True, fidelity_report=res.get("fidelity"))
                    db.add(version)
                    db.commit()
                    current_path = out_path
                    doc.current_version = new_ver
                    db.commit()
                results.append({"type": t, "success": res.get("success"), "detail": res})
            elif t == "highlight_text":
                page = int(op.get("page", 0))
                bbox = op.get("bbox")
                # if find instead of bbox, highlight via find
                if not bbox and op.get("find"):
                    find = op.get("find")
                    matches = pdf_find(current_path, find)
                    # highlight first match as demo; iterate?
                    for m in matches[:5]:
                        bbox = list(m.bounding_box)
                        new_ver = (db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first().version_number + 1)
                        out_path = str(VERSIONS / f"{doc_id}_v{new_ver}.pdf")
                        pdf_highlight(current_path, m.page_number, bbox, out_path)
                        version = Version(document_id=doc_id, version_number=new_ver, file_path=out_path, operation=t, detail=f"AI highlight {find}", is_ai=True)
                        db.add(version)
                        db.commit()
                        current_path = out_path
                        doc.current_version = new_ver
                        db.commit()
                    results.append({"type": t, "success": True, "highlighted": len(matches)})
                elif bbox:
                    new_ver = (db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first().version_number + 1)
                    out_path = str(VERSIONS / f"{doc_id}_v{new_ver}.pdf")
                    pdf_highlight(current_path, page, bbox, out_path)
                    version = Version(document_id=doc_id, version_number=new_ver, file_path=out_path, operation=t, detail=f"AI highlight page {page}", is_ai=True)
                    db.add(version)
                    db.commit()
                    current_path = out_path
                    doc.current_version = new_ver
                    db.commit()
                    results.append({"type": t, "success": True, "version": new_ver})
                else:
                    results.append({"type": t, "success": False, "error": "Need bbox or find"})
            elif t == "extract_text":
                txt = pdf_text_preview(current_path, 15000)
                results.append({"type": t, "success": True, "extracted": txt[:2000]})
            elif t == "extract_table":
                from ..pdf_engine import pdf_extract_table_like
                rows = pdf_extract_table_like(current_path, op.get("page", 0))
                results.append({"type": t, "success": True, "table": rows})
            elif t == "summarize_document":
                txt = pdf_text_preview(current_path, 8000)
                # naive summary: first 500 chars + stats
                summary = f"Document has {doc.page_count} pages. Preview: {txt[:500]}..."
                results.append({"type": t, "success": True, "summary": summary})
            elif t == "rotate_page":
                pages = op.get("pages") or ([op.get("page")] if op.get("page") is not None else [0])
                angle = int(op.get("angle", 90))
                new_ver = (db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first().version_number + 1)
                out_path = str(VERSIONS / f"{doc_id}_v{new_ver}.pdf")
                pdf_rotate(current_path, pages, angle, out_path)
                version = Version(document_id=doc_id, version_number=new_ver, file_path=out_path, operation=t, detail=f"AI rotate {pages}", is_ai=True)
                db.add(version)
                db.commit()
                current_path = out_path
                doc.current_version = new_ver
                db.commit()
                results.append({"type": t, "success": True, "version": new_ver})
            elif t == "delete_page":
                pages = op.get("pages") or ([op.get("page")] if op.get("page") is not None else [0])
                new_ver = (db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first().version_number + 1)
                out_path = str(VERSIONS / f"{doc_id}_v{new_ver}.pdf")
                pdf_delete_pages(current_path, pages, out_path)
                version = Version(document_id=doc_id, version_number=new_ver, file_path=out_path, operation=t, detail=f"AI delete pages {pages}", is_ai=True)
                db.add(version)
                db.commit()
                current_path = out_path
                doc.current_version = new_ver
                db.commit()
                results.append({"type": t, "success": True, "version": new_ver})
            else:
                results.append({"type": t, "success": False, "error": f"Operation {t} not yet implemented in apply path"})
        except Exception as e:
            results.append({"type": t, "success": False, "error": str(e)[:500]})
    # update history
    hist = AIHistory(document_id=doc_id, prompt=validated.get("explanation",""), model=get_configured_provider(db).model, provider_url=get_configured_provider(db).base_url, operation=validated["intent"], status="applied" if any(r.get("success") for r in results) else "failed", response_json={"request": validated, "results": results})
    db.add(hist)
    db.commit()
    audit(db, doc_id, "AI apply", f"{validated['intent']} -> {len([r for r in results if r.get('success')])} succeeded")
    return {"results": results, "applied": True}

@router.get("/history")
def ai_history(document_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(AIHistory)
    if document_id:
        q = q.filter(AIHistory.document_id == document_id)
    rows = q.order_by(AIHistory.created_at.desc()).limit(100).all()
    return [{"id": r.id, "document_id": r.document_id, "prompt": r.prompt, "model": r.model, "provider_url": r.provider_url, "operation": r.operation, "status": r.status, "created_at": r.created_at, "response": r.response_json} for r in rows]

@router.post("/test-connection")
async def test_connection(payload: dict | None = None, db: Session = Depends(get_db)):
    # Payload may override base_url/api_key/model for testing without saving
    base_url = (payload or {}).get("base_url") or (payload or {}).get("AI_BASE_URL")
    api_key = (payload or {}).get("api_key") or (payload or {}).get("AI_API_KEY")
    model = (payload or {}).get("model") or (payload or {}).get("AI_MODEL")
    # if provided, test that provider; else test configured
    if base_url or api_key or model:
        from ..ai_provider import OpenAICompatibleProvider
        prov = OpenAICompatibleProvider(base_url or settings.AI_BASE_URL, api_key or settings.AI_API_KEY, model or settings.AI_MODEL)
    else:
        prov = get_configured_provider(db)
    result = await prov.test_connection()
    return result
