from __future__ import annotations
import os, shutil, uuid, json, tempfile
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models_db import Document, Version, AuditLog
from ..config import settings
from ..pdf_engine import pdf_page_count, pdf_text_preview, pdf_find, pdf_replace, pdf_highlight, pdf_rotate, pdf_delete_pages, pdf_reorder, pdf_merge, pdf_split, pdf_extract_text

router = APIRouter(prefix="/api/documents", tags=["documents"])

STORAGE = Path(settings.STORAGE_DIR)
ORIGINALS = STORAGE / "originals"
VERSIONS = STORAGE / "versions"
for p in [ORIGINALS, VERSIONS]:
    p.mkdir(parents=True, exist_ok=True)

def audit(db: Session, doc_id: int | None, action: str, detail: str = ""):
    try:
        db.add(AuditLog(document_id=doc_id, action=action, detail=detail))
        db.commit()
    except Exception:
        pass

@router.get("/")
def list_documents(db: Session = Depends(get_db), q: str | None = None, favorite: bool | None = None, include_deleted: bool = False):
    query = db.query(Document)
    if not include_deleted:
        query = query.filter(Document.is_deleted == False)
    if favorite is not None:
        query = query.filter(Document.is_favorite == favorite)
    if q:
        query = query.filter(Document.filename.ilike(f"%{q}%"))
    docs = query.order_by(Document.updated_at.desc()).all()
    # Also filter by text cache if q and not found in filename
    if q:
        text_matches = []
        for d in docs:
            if q.lower() in (d.filename or "").lower() or q.lower() in (d.cached_text or "").lower():
                text_matches.append(d)
        # also consider not yet filtered
        docs = text_matches
    return [{"id": d.id, "filename": d.filename, "page_count": d.page_count, "file_size": d.file_size, "is_favorite": d.is_favorite, "is_deleted": d.is_deleted, "current_version": d.current_version, "created_at": d.created_at, "updated_at": d.updated_at, "title": d.title} for d in docs]

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files allowed")
    content = await file.read()
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(400, "File too large (100MB limit)")
    # Validate PDF magic
    if not content.startswith(b"%PDF"):
        raise HTTPException(400, "Invalid PDF file")
    fid = str(uuid.uuid4())
    orig_path = ORIGINALS / f"{fid}_{file.filename}"
    orig_path.write_bytes(content)
    try:
        pages = pdf_page_count(str(orig_path))
    except Exception:
        pages = 0
    text_cache = pdf_text_preview(str(orig_path), 10000)
    doc = Document(filename=file.filename, original_path=str(orig_path), page_count=pages, file_size=len(content), cached_text=text_cache)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    # Create v1 version copy
    v1_path = VERSIONS / f"{doc.id}_v1.pdf"
    shutil.copy(str(orig_path), str(v1_path))
    v = Version(document_id=doc.id, version_number=1, file_path=str(v1_path), operation="Original", detail="Original upload")
    db.add(v)
    db.commit()
    audit(db, doc.id, "upload", f"Uploaded {file.filename} ({pages} pages)")
    return {"id": doc.id, "filename": doc.filename, "page_count": pages, "version": 1}

@router.get("/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    versions = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number).all()
    return {"id": doc.id, "filename": doc.filename, "page_count": doc.page_count, "file_size": doc.file_size, "is_favorite": doc.is_favorite, "current_version": doc.current_version, "created_at": doc.created_at, "updated_at": doc.updated_at, "original_path": doc.original_path, "versions": [{"version": v.version_number, "operation": v.operation, "detail": v.detail, "is_ai": v.is_ai, "created_at": v.created_at, "fidelity_report": v.fidelity_report} for v in versions]}

@router.put("/{doc_id}")
def update_document(doc_id: int, payload: dict, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    if "filename" in payload:
        doc.filename = payload["filename"]
    if "is_favorite" in payload:
        doc.is_favorite = bool(payload["is_favorite"])
    if "title" in payload:
        doc.title = payload["title"]
    db.commit()
    return {"ok": True}

@router.post("/{doc_id}/duplicate")
def duplicate_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    latest = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first()
    if not latest:
        raise HTTPException(400, "No version found")
    new_doc = Document(filename=f"Copy of {doc.filename}", original_path=latest.file_path, page_count=doc.page_count, file_size=doc.file_size, cached_text=doc.cached_text)
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    # copy version
    new_path = VERSIONS / f"{new_doc.id}_v1.pdf"
    shutil.copy(latest.file_path, str(new_path))
    v = Version(document_id=new_doc.id, version_number=1, file_path=str(new_path), operation="Duplicated", detail=f"From doc {doc_id} v{latest.version_number}")
    db.add(v)
    db.commit()
    audit(db, new_doc.id, "duplicate", f"Duplicated from {doc_id}")
    return {"id": new_doc.id}

@router.delete("/{doc_id}")
def delete_document(doc_id: int, permanent: bool = False, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    if permanent:
        db.delete(doc)
        db.query(Version).filter(Version.document_id == doc_id).delete()
        db.commit()
        audit(db, None, "delete_permanent", f"Deleted doc {doc_id}")
    else:
        doc.is_deleted = True
        db.commit()
        audit(db, doc_id, "delete", "Moved to trash")
    return {"ok": True}

@router.post("/{doc_id}/restore")
def restore_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    doc.is_deleted = False
    db.commit()
    return {"ok": True}

@router.get("/{doc_id}/file")
def get_file(doc_id: int, version: int | None = None, db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    if version:
        v = db.query(Version).filter(Version.document_id == doc_id, Version.version_number == version).first()
        if not v:
            raise HTTPException(404, "Version not found")
        path = v.file_path
    else:
        # latest
        v = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first()
        path = v.file_path if v else doc.original_path
    if not Path(path).exists():
        raise HTTPException(404, "File not found on disk")
    audit(db, doc_id, "open", f"Opened version {version or 'latest'}")
    return FileResponse(path, media_type="application/pdf", filename=doc.filename)

@router.get("/{doc_id}/text")
def get_text(doc_id: int, version: int | None = None, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    v = None
    if version:
        v = db.query(Version).filter(Version.document_id == doc_id, Version.version_number == version).first()
    else:
        v = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first()
    path = v.file_path if v else doc.original_path
    text = pdf_text_preview(path, 20000)
    return {"text": text}

@router.post("/{doc_id}/find")
def find_text(doc_id: int, payload: dict, db: Session = Depends(get_db)):
    query = payload.get("query") or payload.get("find") or ""
    if not query:
        raise HTTPException(400, "query required")
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    v = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first()
    path = v.file_path if v else doc.original_path
    matches = pdf_find(path, query)
    out = []
    for m in matches:
        out.append({"matched_text": m.matched_text, "page_number": m.page_number, "bounding_box": m.bounding_box, "font": getattr(m.font_info, "name", "") if hasattr(m, "font_info") else ""})
    audit(db, doc_id, "find", f"Find '{query}' -> {len(out)} matches")
    return {"matches": out, "count": len(out)}

@router.post("/{doc_id}/replace")
def replace_text(doc_id: int, payload: dict, db: Session = Depends(get_db)):
    find_t = payload.get("find") or payload.get("query")
    replace_t = payload.get("replace", "")
    scope = payload.get("scope", "document")
    dry_run = bool(payload.get("dry_run", False))
    if not find_t:
        raise HTTPException(400, "find required")
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    v = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first()
    path = v.file_path if v else doc.original_path
    # dry_run uses replacement logic but not saving version
    if dry_run:
        tmp = tempfile.mktemp(suffix=".pdf")
        res = pdf_replace(path, find_t, replace_t, tmp, dry_run=False)
        # we did real replace to tmp; count fidelity
        # Clean tmp
        try: Path(tmp).unlink()
        except: pass
        return {"preview": res, "dry_run": True, "find": find_t, "replace": replace_t}
    else:
        new_version_num = (v.version_number + 1) if v else 1
        out_path = str(VERSIONS / f"{doc_id}_v{new_version_num}.pdf")
        res = pdf_replace(path, find_t, replace_t, out_path, dry_run=False)
        if not res.get("success"):
            # cleanup failed file if exists
            try: Path(out_path).unlink()
            except: pass
            raise HTTPException(422, f"Replace failed: {res.get('error') or res}")
        fidelity = res.get("fidelity")
        new_v = Version(document_id=doc_id, version_number=new_version_num, file_path=out_path, operation="replace_text", detail=f"Replace '{find_t}' -> '{replace_t}'", is_ai=bool(payload.get("is_ai", False)), fidelity_report=fidelity)
        db.add(new_v)
        doc.current_version = new_version_num
        doc.cached_text = pdf_text_preview(out_path, 10000)
        db.commit()
        audit(db, doc_id, "edit", f"Replace '{find_t}'->'{replace_t}' -> v{new_version_num}")
        return {"success": True, "version": new_version_num, "fidelity": fidelity, "matches": res.get("matches")}

@router.post("/{doc_id}/highlight")
def highlight(doc_id: int, payload: dict, db: Session = Depends(get_db)):
    page = int(payload.get("page", 0))
    bbox = payload.get("bbox") or payload.get("quad_points")
    if not bbox:
        raise HTTPException(400, "bbox required [x1,y1,x2,y2]")
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    v = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first()
    path = v.file_path if v else doc.original_path
    new_version_num = (v.version_number + 1) if v else 1
    out_path = str(VERSIONS / f"{doc_id}_v{new_version_num}.pdf")
    try:
        pdf_highlight(path, page, list(map(float, bbox)), out_path)
    except Exception as e:
        raise HTTPException(422, f"Highlight failed: {e}")
    new_v = Version(document_id=doc_id, version_number=new_version_num, file_path=out_path, operation="highlight_text", detail=f"Highlight page {page}", is_ai=bool(payload.get("is_ai", False)))
    db.add(new_v)
    doc.current_version = new_version_num
    db.commit()
    audit(db, doc_id, "annotation", f"Highlight page {page}")
    return {"success": True, "version": new_version_num}

@router.post("/{doc_id}/annotate")
def annotate(doc_id: int, payload: dict, db: Session = Depends(get_db)):
    # generic annotation: text note etc via add_annotation? fallback to highlight
    page = int(payload.get("page", 0))
    bbox = payload.get("bbox", [100,100,200,150])
    content = payload.get("content", "Note")
    atype = payload.get("annotation_type", "text")
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    v = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first()
    path = v.file_path if v else doc.original_path
    new_version_num = (v.version_number + 1) if v else 1
    out_path = str(VERSIONS / f"{doc_id}_v{new_version_num}.pdf")
    try:
        # Use pdf_edit_engine add_annotation
        from pdf_edit_engine.annotations import add_annotation
        add_annotation(path, page, tuple(bbox), content, out_path)
    except Exception as e:
        # fallback highlight
        try:
            pdf_highlight(path, page, bbox, out_path)
        except Exception as e2:
            raise HTTPException(422, f"Annotation failed: {e} / {e2}")
    new_v = Version(document_id=doc_id, version_number=new_version_num, file_path=out_path, operation="add_annotation", detail=f"{atype}: {content[:100]}")
    db.add(new_v)
    doc.current_version = new_version_num
    db.commit()
    audit(db, doc_id, "annotation", f"Annotate {atype}")
    return {"success": True, "version": new_version_num}

@router.post("/{doc_id}/redact")
def redact(doc_id: int, payload: dict, db: Session = Depends(get_db)):
    # Genuine redaction: white out region and save copy. Use pikepdf to draw white rectangle over region.
    page_idx = int(payload.get("page", 0))
    bbox = payload.get("bbox")
    if not bbox or len(bbox)!=4:
        raise HTTPException(400, "bbox [x1,y1,x2,y2] required")
    confirm = payload.get("confirm", False)
    if not confirm:
        # preview mode: just return preview flag
        return {"preview": True, "page": page_idx, "bbox": bbox, "message": "Preview: white rectangle will cover selected area. Confirm to apply."}
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    v = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first()
    path = v.file_path if v else doc.original_path
    new_version_num = (v.version_number + 1) if v else 1
    out_path = str(VERSIONS / f"{doc_id}_v{new_version_num}.pdf")
    # Simple redaction: add white rectangle via pikepdf content stream injection
    try:
        import pikepdf
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.colors import white
        import io
        x1,y1,x2,y2 = map(float, bbox)
        # create overlay pdf with white rect
        overlay_tmp = tempfile.mktemp(suffix=".pdf")
        # need page size: open original
        with pikepdf.open(path) as pdf:
            page = pdf.pages[page_idx]
            media = page.MediaBox
            pw = float(media[2]) - float(media[0])
            ph = float(media[3]) - float(media[1])
        c = rl_canvas.Canvas(overlay_tmp, pagesize=(pw, ph))
        c.setFillColor(white)
        c.setStrokeColor(white)
        # y in PDF is bottom-origin; bbox assumed same
        c.rect(x1, y1, x2-x1, y2-y1, stroke=0, fill=1)
        c.showPage()
        c.save()
        with pikepdf.open(path) as pdf:
            overlay = pikepdf.open(overlay_tmp)
            ov_page = overlay.pages[0]
            pdf.pages[page_idx].add_overlay(ov_page)
            pdf.save(out_path)
            overlay.close()
        Path(overlay_tmp).unlink(missing_ok=True)
    except Exception as e:
        raise HTTPException(422, f"Redact failed: {e}")
    new_v = Version(document_id=doc_id, version_number=new_version_num, file_path=out_path, operation="redact_region", detail=f"Redact page {page_idx} {bbox}")
    db.add(new_v)
    doc.current_version = new_version_num
    db.commit()
    audit(db, doc_id, "redaction", f"Redacted page {page_idx}")
    return {"success": True, "version": new_version_num}

@router.post("/{doc_id}/pages/rotate")
def rotate(doc_id: int, payload: dict, db: Session = Depends(get_db)):
    pages = payload.get("pages") or ([payload.get("page")] if payload.get("page") is not None else [])
    angle = int(payload.get("angle", 90))
    if not pages:
        raise HTTPException(400, "pages required")
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    v = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first()
    path = v.file_path if v else doc.original_path
    new_version_num = (v.version_number + 1) if v else 1
    out_path = str(VERSIONS / f"{doc_id}_v{new_version_num}.pdf")
    pdf_rotate(path, pages, angle, out_path)
    new_v = Version(document_id=doc_id, version_number=new_version_num, file_path=out_path, operation="rotate_page", detail=f"Rotate {pages} by {angle}")
    db.add(new_v)
    doc.current_version = new_version_num
    db.commit()
    audit(db, doc_id, "page_operation", f"Rotate pages {pages}")
    return {"success": True, "version": new_version_num}

@router.post("/{doc_id}/pages/delete")
def delete_pages(doc_id: int, payload: dict, db: Session = Depends(get_db)):
    pages = payload.get("pages") or []
    if not pages:
        raise HTTPException(400, "pages required")
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    v = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first()
    path = v.file_path if v else doc.original_path
    new_version_num = (v.version_number + 1) if v else 1
    out_path = str(VERSIONS / f"{doc_id}_v{new_version_num}.pdf")
    pdf_delete_pages(path, pages, out_path)
    new_v = Version(document_id=doc_id, version_number=new_version_num, file_path=out_path, operation="delete_page", detail=f"Delete {pages}")
    db.add(new_v)
    doc.current_version = new_version_num
    # update page count
    try: doc.page_count = pdf_page_count(out_path)
    except: pass
    db.commit()
    audit(db, doc_id, "page_operation", f"Delete pages {pages}")
    return {"success": True, "version": new_version_num}

@router.post("/{doc_id}/pages/duplicate")
def duplicate_page(doc_id: int, payload: dict, db: Session = Depends(get_db)):
    page = int(payload.get("page", 0))
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    v = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first()
    path = v.file_path if v else doc.original_path
    new_version_num = (v.version_number + 1) if v else 1
    out_path = str(VERSIONS / f"{doc_id}_v{new_version_num}.pdf")
    import pikepdf
    with pikepdf.open(path) as pdf:
        pdf.pages.append(pdf.pages[page])
        pdf.save(out_path)
    new_v = Version(document_id=doc_id, version_number=new_version_num, file_path=out_path, operation="duplicate_page", detail=f"Duplicate page {page}")
    db.add(new_v)
    doc.current_version = new_version_num
    try: doc.page_count = pdf_page_count(out_path)
    except: pass
    db.commit()
    audit(db, doc_id, "page_operation", f"Duplicate page {page}")
    return {"success": True, "version": new_version_num}

@router.post("/{doc_id}/pages/reorder")
def reorder(doc_id: int, payload: dict, db: Session = Depends(get_db)):
    order = payload.get("order")
    if not order:
        raise HTTPException(400, "order required")
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    v = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first()
    path = v.file_path if v else doc.original_path
    new_version_num = (v.version_number + 1) if v else 1
    out_path = str(VERSIONS / f"{doc_id}_v{new_version_num}.pdf")
    pdf_reorder(path, order, out_path)
    new_v = Version(document_id=doc_id, version_number=new_version_num, file_path=out_path, operation="reorder_pages", detail=f"Reorder {order}")
    db.add(new_v)
    doc.current_version = new_version_num
    db.commit()
    audit(db, doc_id, "page_operation", f"Reorder pages")
    return {"success": True, "version": new_version_num}

@router.post("/{doc_id}/pages/insert-blank")
def insert_blank(doc_id: int, payload: dict, db: Session = Depends(get_db)):
    index = int(payload.get("index", -1))
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    v = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first()
    path = v.file_path if v else doc.original_path
    new_version_num = (v.version_number + 1) if v else 1
    out_path = str(VERSIONS / f"{doc_id}_v{new_version_num}.pdf")
    # create blank page pdf
    blank = tempfile.mktemp(suffix=".pdf")
    from ..pdf_engine import create_blank_pdf
    create_blank_pdf(blank)
    import pikepdf
    with pikepdf.open(path) as pdf:
        blank_pdf = pikepdf.open(blank)
        if index < 0 or index >= len(pdf.pages):
            pdf.pages.append(blank_pdf.pages[0])
        else:
            # insert at index: create new pdf
            new_pdf = pikepdf.Pdf.new()
            for i, p in enumerate(pdf.pages):
                if i == index:
                    new_pdf.pages.append(blank_pdf.pages[0])
                new_pdf.pages.append(p)
            if index == len(pdf.pages):
                new_pdf.pages.append(blank_pdf.pages[0])
            new_pdf.save(out_path)
            blank_pdf.close()
            new_v = Version(document_id=doc_id, version_number=new_version_num, file_path=out_path, operation="insert_blank_page", detail=f"Insert blank at {index}")
            db.add(new_v)
            doc.current_version = new_version_num
            try: doc.page_count = pdf_page_count(out_path)
            except: pass
            db.commit()
            audit(db, doc_id, "page_operation", f"Insert blank page")
            Path(blank).unlink(missing_ok=True)
            return {"success": True, "version": new_version_num}
        pdf.save(out_path)
        blank_pdf.close()
    Path(blank).unlink(missing_ok=True)
    new_v = Version(document_id=doc_id, version_number=new_version_num, file_path=out_path, operation="insert_blank_page", detail=f"Insert blank at {index}")
    db.add(new_v)
    doc.current_version = new_version_num
    try: doc.page_count = pdf_page_count(out_path)
    except: pass
    db.commit()
    audit(db, doc_id, "page_operation", f"Insert blank page")
    return {"success": True, "version": new_version_num}

@router.post("/{doc_id}/split")
def split(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    v = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first()
    path = v.file_path if v else doc.original_path
    out_dir = str(VERSIONS / f"{doc_id}_split_{uuid.uuid4().hex[:6]}")
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    outputs = pdf_split(path, out_dir)
    return {"outputs": outputs, "count": len(outputs)}

@router.post("/merge")
def merge(payload: dict, db: Session = Depends(get_db)):
    doc_ids = payload.get("document_ids") or payload.get("ids") or []
    if len(doc_ids) < 2:
        raise HTTPException(400, "At least 2 documents required")
    paths = []
    for did in doc_ids:
        doc = db.query(Document).filter(Document.id == did).first()
        if not doc:
            raise HTTPException(404, f"Document {did} not found")
        v = db.query(Version).filter(Version.document_id == did).order_by(Version.version_number.desc()).first()
        paths.append(v.file_path if v else doc.original_path)
    merged_name = payload.get("filename", "merged.pdf")
    fid = str(uuid.uuid4())
    out_path = str(VERSIONS / f"merged_{fid}.pdf")
    pdf_merge(paths, out_path)
    # create new document entry for merged
    try: pages = pdf_page_count(out_path)
    except: pages = 0
    text_cache = pdf_text_preview(out_path, 10000)
    doc = Document(filename=merged_name, original_path=out_path, page_count=pages, file_size=Path(out_path).stat().st_size, cached_text=text_cache)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    v = Version(document_id=doc.id, version_number=1, file_path=out_path, operation="merge_pdf", detail=f"Merged {doc_ids}")
    db.add(v)
    db.commit()
    audit(db, doc.id, "merge", f"Merged {doc_ids}")
    return {"id": doc.id, "filename": merged_name}

@router.get("/{doc_id}/versions")
def list_versions(doc_id: int, db: Session = Depends(get_db)):
    versions = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number).all()
    return [{"version": v.version_number, "operation": v.operation, "detail": v.detail, "is_ai": v.is_ai, "created_at": v.created_at, "fidelity_report": v.fidelity_report, "file_path": v.file_path} for v in versions]

@router.get("/{doc_id}/export")
def export(doc_id: int, version: int | None = None, type: str = "edited", db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Not found")
    if type == "original":
        path = doc.original_path
        fname = f"original_{doc.filename}"
    else:
        if version:
            v = db.query(Version).filter(Version.document_id == doc_id, Version.version_number == version).first()
            if not v:
                raise HTTPException(404, "Version not found")
            path = v.file_path
            fname = f"v{version}_{doc.filename}"
        else:
            v = db.query(Version).filter(Version.document_id == doc_id).order_by(Version.version_number.desc()).first()
            path = v.file_path if v else doc.original_path
            fname = doc.filename
    audit(db, doc_id, "export", f"Export {type} v{version}")
    return FileResponse(path, media_type="application/pdf", filename=fname)
