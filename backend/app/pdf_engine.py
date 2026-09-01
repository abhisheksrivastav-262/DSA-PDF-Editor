from __future__ import annotations
import shutil
import tempfile
from pathlib import Path
from typing import Any

# Wrapper around pdf-edit-engine core
try:
    from pdf_edit_engine import find, replace, replace_all, batch_replace, Edit, get_text, get_text_layout, get_fonts, extract_bbox_text
    from pdf_edit_engine import merge_pdfs as engine_merge
    from pdf_edit_engine import split_pdf as engine_split
    from pdf_edit_engine import rotate_pages as engine_rotate
    from pdf_edit_engine import delete_pages as engine_delete
    from pdf_edit_engine import reorder_pages as engine_reorder
    from pdf_edit_engine.annotations import get_annotations, add_annotation
    from pdf_edit_engine import add_highlight
except Exception as e:
    # fallback stubs for dev without engine
    find = None  # type: ignore
    replace = None  # type: ignore
    get_text = None  # type: ignore

import pikepdf

def pdf_page_count(path: str) -> int:
    with pikepdf.open(path) as pdf:
        return len(pdf.pages)

def pdf_text_preview(path: str, max_chars: int = 8000) -> str:
    try:
        from pdf_edit_engine import get_text
        text = get_text(path)
        if isinstance(text, list):
            # get_text may return blocks
            text = "\n".join([b.text if hasattr(b, "text") else str(b) for b in text])
        return str(text)[:max_chars]
    except Exception:
        # fallback via pikepdf text extraction? use pdfminer
        try:
            from pdfminer.high_level import extract_text
            return extract_text(path)[:max_chars]
        except Exception:
            return ""

def pdf_find(path: str, query: str):
    from pdf_edit_engine import find as _find
    return _find(path, query)

def pdf_replace(path: str, find_text: str, replace_text: str, output: str, dry_run: bool = False):
    from pdf_edit_engine import find as _find, replace as _replace, replace_all as _replace_all
    # Use replace_all for document scope
    # If find_text empty -> error
    matches = _find(path, find_text)
    if not matches:
        return {"success": False, "matches": 0, "error": "No matches found", "fidelity": None}
    # Use replace_all
    result = _replace_all(path, find_text, replace_text, output, dry_run=dry_run)
    # _replace_all returns list[EditResult] or single? Check engine - it returns list?
    # In engine, replace_all returns list[EditResult] ?
    # Actually check: surgeon.replace_all signature -> returns list[EditResult]
    # We'll normalize
    if isinstance(result, list):
        # take first or aggregate?
        # For simplicity, if any succeeded
        successes = [r for r in result if getattr(r, "success", False)]
        fidelity = result[0].fidelity_report.to_dict() if result and hasattr(result[0], "fidelity_report") else None
        return {"success": bool(successes), "matches": len(matches), "results": [r.to_dict() if hasattr(r, "to_dict") else str(r) for r in result], "fidelity": fidelity}
    else:
        # single result
        return {"success": getattr(result, "success", False), "matches": len(matches), "results": [result.to_dict() if hasattr(result, "to_dict") else str(result)], "fidelity": getattr(result, "fidelity_report", None).to_dict() if hasattr(result, "fidelity_report") else None}

def pdf_highlight(path: str, page: int, bbox_or_quad: list[float], output: str):
    from pdf_edit_engine import add_highlight
    # bbox to quad_points
    # If bbox 4 values -> derive quad
    if len(bbox_or_quad) == 4:
        x1,y1,x2,y2 = bbox_or_quad
        quad = [x1,y2, x2,y2, x1,y1, x2,y1]
    else:
        quad = bbox_or_quad
    return add_highlight(path, page, quad, output)

def pdf_rotate(path: str, pages: list[int], angle: int, output: str):
    from pdf_edit_engine import rotate_pages
    return rotate_pages(path, pages, angle, output)

def pdf_delete_pages(path: str, pages: list[int], output: str):
    from pdf_edit_engine import delete_pages
    return delete_pages(path, pages, output)

def pdf_reorder(path: str, order: list[int], output: str):
    from pdf_edit_engine import reorder_pages
    return reorder_pages(path, order, output)

def pdf_merge(paths: list[str], output: str):
    from pdf_edit_engine import merge_pdfs
    return merge_pdfs(paths, output)

def pdf_split(path: str, out_dir: str):
    from pdf_edit_engine import split_pdf
    return split_pdf(path, out_dir)

def pdf_extract_text(path: str) -> str:
    return pdf_text_preview(path, 20000)

def pdf_extract_table_like(path: str, page: int = 0):
    # Use get_text_layout for table extraction heuristic
    try:
        from pdf_edit_engine import get_text_layout
        layout = get_text_layout(path)
        # filter by page
        blocks = [b for b in layout if getattr(b, "page", 0) == page]
        # simple: return blocks as rows
        rows = []
        for b in blocks:
            txt = getattr(b, "text", str(b))
            rows.append(txt)
        return rows
    except Exception as e:
        return {"error": str(e)}

def create_blank_pdf(output: str, width: float = 612, height: float = 792):
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(output, pagesize=(width, height))
    c.showPage()
    c.save()
    return output
