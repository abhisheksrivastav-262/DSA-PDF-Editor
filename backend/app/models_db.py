from __future__ import annotations
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, JSON
from sqlalchemy.sql import func
from .database import Base
import datetime

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    current_version = Column(Integer, default=1)
    page_count = Column(Integer, default=0)
    file_size = Column(Integer, default=0)
    is_favorite = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    # metadata
    title = Column(String, default="")
    # text cache
    cached_text = Column(Text, default="")

class Version(Base):
    __tablename__ = "versions"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, index=True)
    version_number = Column(Integer)
    file_path = Column(String)
    operation = Column(String)  # e.g. replace_text, annotation, redaction
    detail = Column(Text, default="")
    is_ai = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    fidelity_report = Column(JSON, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, nullable=True)
    action = Column(String)  # upload, open, edit, AI request, preview, apply, etc.
    detail = Column(Text, default="")
    user = Column(String, default="Admin")
    created_at = Column(DateTime, default=func.now())

class AIHistory(Base):
    __tablename__ = "ai_history"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, nullable=True)
    prompt = Column(Text)
    model = Column(String, default="")
    provider_url = Column(String, default="")
    operation = Column(String, default="")
    status = Column(String, default="pending")  # success, failed, preview
    response_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())

class AppSettings(Base):
    __tablename__ = "app_settings"
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
