"""
Backend configuration — loads from .env via pydantic-settings.
All other modules import from here; no raw os.getenv calls elsewhere.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from pathlib import Path
import json
from typing import Annotated

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AfriHealth Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Model — Local or Remote
    # For online deployment, leave MODEL_PATH empty and set LLM_PROVIDER to "huggingface", "gemini", or "groq"
    # Core LLM settings - We default to a highly optimized Q4 GGUF of Phi-3-mini to pass the ADTC 7GB memory rule
    MODEL_PATH: str = "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
    LLM_PROVIDER: str = "local"  # Options: "local", "huggingface", "gemini", "groq"
    AUTO_DOWNLOAD_MODEL: bool = False
    HUGGINGFACE_API_KEY: str = ""  # Free inference API at huggingface.co
    HUGGINGFACE_MODEL_ID: str = "Qwen/Qwen2.5-7B-Instruct"
    GROQ_API_KEY: str = ""  # Fast LLM API
    EMBEDDING_MODEL: str = str(BASE_DIR / "models" / "embedding" / "all-MiniLM-L6-v2")
    ENABLE_TRANSLATION_MODELS: bool = False

    # Database
    DB_PATH: str = str(BASE_DIR / "data" / "afrihealth.db")

    # RAG
    VECTOR_DB_PATH: str = str(BASE_DIR / "data" / "vector_db" / "chroma_db")
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # LLM parameters
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_MAX_TOKENS: int = 512
    DEFAULT_TOP_P: float = 0.9
    NUM_THREADS: int = 4
    CONTEXT_LENGTH: int = 2048

    # CORS. Exact origins remain supported for production; the local regex
    # covers Streamlit/SPA development ports without requiring code changes.
    ALLOWED_ORIGINS: str | list[str] = ["http://localhost:8501", "http://127.0.0.1:8501"]
    ALLOWED_ORIGIN_REGEX: str = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    # API Keys
    GEMINI_API_KEY: str = ""

    # Password recovery. `local` returns a one-time token for an offline
    # deployment; `email` requires SMTP and a user email address.
    AUTH_RECOVERY_MODE: str = "local"
    PASSWORD_RESET_TTL_MINUTES: int = 30
    PASSWORD_RESET_ADMIN_TOKEN: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_USE_TLS: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value):
        """Accept common deployment labels in addition to true/false values."""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod", "off", "0", "false"}:
                return False
            if normalized in {"debug", "development", "dev", "on", "1", "true"}:
                return True
        return value

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value):
        """Accept a JSON list or comma-separated .env value."""
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                return json.loads(raw)
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
        return value

    model_config = {"env_file": str(BASE_DIR.parent / ".env"), "extra": "ignore"}


settings = Settings()


def resolve_project_path(value: str) -> Path:
    """Resolve relative paths from the repository root, not the shell cwd.
    If value is an HTTP/HTTPS URL, return it as-is (as a Path wrapping is not appropriate).
    """
    if value and (value.startswith("http://") or value.startswith("https://")):
        return Path(value)  # caller must handle URL strings separately
    path = Path(value).expanduser()
    return path if path.is_absolute() else BASE_DIR.parent / path
