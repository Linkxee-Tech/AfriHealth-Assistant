"""
Backend configuration — loads from .env via pydantic-settings.
All other modules import from here; no raw os.getenv calls elsewhere.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AfriHealth Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Model
    MODEL_PATH: str = str(BASE_DIR / "models" / "llm" / "llama-3-8b-q4.gguf")
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

    # CORS
    ALLOWED_ORIGINS: list = ["http://localhost:8501", "http://127.0.0.1:8501"]

    # API Keys
    GEMINI_API_KEY: str = ""

    model_config = {"env_file": str(BASE_DIR.parent / ".env"), "extra": "ignore"}


settings = Settings()
