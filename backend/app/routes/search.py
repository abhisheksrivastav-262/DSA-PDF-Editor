from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models_db import Document, Version, AIHistory, AuditLog

router = APIRouter(prefix="/api", tags=["search"])

@router.get("/search")
def global_search(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    results = []
    # documents by filename
    docs = db.query(Document).filter(Document.filename.ilike(f"%{q}%"), Document.is_deleted==False).limit(10).all()
    for d in docs:
        results.append({"type": "document", "id": d.id, "title": d.filename, "detail": f"{d.page_count} pages", "document_id": d.id})
    # documents by cached text
    docs2 = db.query(Document).filter(Document.cached_text.ilike(f"%{q}%"), Document.is_deleted==False).limit(10).all()
    for d in docs2:
        if d.id not in [r["document_id"] for r in results]:
            results.append({"type": "document_text", "id": d.id, "title": d.filename, "detail": f"Text match in {d.filename}", "document_id": d.id})
    # audit logs
    logs = db.query(AuditLog).filter(AuditLog.detail.ilike(f"%{q}%")).order_by(AuditLog.created_at.desc()).limit(5).all()
    for l in logs:
        results.append({"type": "audit", "id": l.id, "title": f"Audit: {l.action}", "detail": l.detail[:100], "document_id": l.document_id})
    # ai history
    hist = db.query(AIHistory).filter(AIHistory.prompt.ilike(f"%{q}%")).order_by(AIHistory.created_at.desc()).limit(5).all()
    for h in hist:
        results.append({"type": "ai", "id": h.id, "title": f"AI: {h.operation}", "detail": h.prompt[:100], "document_id": h.document_id})
    return {"query": q, "results": results, "count": len(results)}

@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    total_docs = db.query(Document).filter(Document.is_deleted==False).count()
    total_versions = db.query(Version).count()
    ai_ops = db.query(AIHistory).count()
    recent = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(10).all()
    return {"total_documents": total_docs, "edited_pdfs": total_versions - total_docs if total_versions>=total_docs else 0, "ai_operations": ai_ops, "recent_activity": [{"action": r.action, "detail": r.detail, "document_id": r.document_id, "created_at": r.created_at} for r in recent]}

@router.get("/audit")
def audit_list(document_id: int | None = None, limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(AuditLog)
    if document_id:
        q = q.filter(AuditLog.document_id == document_id)
    rows = q.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [{"id": r.id, "document_id": r.document_id, "action": r.action, "detail": r.detail, "user": r.user, "created_at": r.created_at} for r in rows]
