from __future__ import annotations
import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    AI_BASE_URL: str = os.getenv("AI_BASE_URL", "")
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_MODEL: str = os.getenv("AI_MODEL", "")
    AI_TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.2"))
    AI_MAX_TOKENS: int = int(os.getenv("AI_MAX_TOKENS", "4096"))
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", str(Path(__file__).parent.parent / "storage"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{Path(__file__).parent.parent / 'editor.db'}")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production-please-rotate")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
