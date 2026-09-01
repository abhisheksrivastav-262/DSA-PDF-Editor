from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models_db import AppSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])

SENSITIVE_KEYS = {"AI_API_KEY"}

def get_all_settings(db: Session):
    rows = db.query(AppSettings).all()
    return {r.key: r.value for r in rows}

@router.get("/ai")
def get_ai_settings(db: Session = Depends(get_db)):
    data = get_all_settings(db)
    # mask key
    masked = {}
    for k in ["AI_BASE_URL","AI_API_KEY","AI_MODEL","AI_TEMPERATURE","AI_MAX_TOKENS","AI_EXTRA_HEADERS"]:
        v = data.get(k, "")
        if k == "AI_API_KEY" and v:
            masked[k] = "****" + v[-4:] if len(v)>4 else "****"
            masked[k+"_configured"] = True
        else:
            masked[k] = v
            if k == "AI_API_KEY":
                masked[k+"_configured"] = bool(v)
    return masked

@router.post("/ai")
def save_ai_settings(payload: dict, db: Session = Depends(get_db)):
    allowed = {"AI_BASE_URL","AI_API_KEY","AI_MODEL","AI_TEMPERATURE","AI_MAX_TOKENS","AI_EXTRA_HEADERS"}
    for k, v in payload.items():
        if k not in allowed:
            continue
        # Don't overwrite API key if masked
        if k == "AI_API_KEY" and v and v.startswith("****"):
            continue
        # validate
        if k == "AI_TEMPERATURE":
            try: float(v)
            except: raise HTTPException(400, "Invalid temperature")
        if k == "AI_MAX_TOKENS":
            try: int(v)
            except: raise HTTPException(400, "Invalid max_tokens")
        existing = db.query(AppSettings).filter(AppSettings.key == k).first()
        if existing:
            existing.value = str(v)
        else:
            db.add(AppSettings(key=k, value=str(v)))
    db.commit()
    return {"ok": True}

@router.get("/")
def get_all(db: Session = Depends(get_db)):
    data = get_all_settings(db)
    # hide sensitive
    for k in SENSITIVE_KEYS:
        if k in data and data[k]:
            data[k] = "****" + data[k][-4:] if len(data[k])>4 else "****"
    return data
