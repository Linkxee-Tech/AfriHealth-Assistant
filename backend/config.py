"""
Backend configuration — loads from .env via pydantic-settings.
All other modules import from here; no raw os.getenv calls elsewhere.
"""

from pydantic_settings import BaseSettings
from pydantic_settings import NoDecode
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

    # Model
    MODEL_PATH: str = str(BASE_DIR / "models" / "llm" / "Llama-3.2-3B-Instruct-Q4_K_M.gguf")
    EMBEDDING_MODEL: str = str(BASE_DIR / "models" / "embedding" / "all-MiniLM-L6-v2")

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
    ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = ["http://localhost:8501", "http://127.0.0.1:8501"]
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
    """Resolve relative paths from the repository root, not the shell cwd."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else BASE_DIR.parent / path
