"""
Embedding service — wraps sentence-transformers (all-MiniLM-L6-v2).
Falls back to a zero-vector stub when the model is not installed.
"""

from pathlib import Path
from typing import List

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_EMBEDDINGS_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    _EMBEDDINGS_AVAILABLE = True
except ImportError:
    logger.warning("sentence-transformers not installed — embedding stub mode.")


class EmbeddingService:
    def __init__(self, model_path: str = None):
        self.model_path = model_path or settings.EMBEDDING_MODEL
        self._model = None
        self._loaded = False

    def load_model(self):
        if self._loaded:
            return
        if not _EMBEDDINGS_AVAILABLE:
            logger.warning("sentence-transformers unavailable — stub embeddings.")
            self._loaded = True
            return
        try:
            logger.info("Loading embedding model from %s …", self.model_path)
            if Path(self.model_path).exists():
                self._model = SentenceTransformer(self.model_path)
            else:
                # Download from HuggingFace if not cached locally
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
            self._loaded = True
            logger.info("Embedding model loaded.")
        except Exception as exc:
            logger.error("Failed to load embedding model: %s", exc)
            self._loaded = True

    def embed(self, text: str) -> List[float]:
        if not self._loaded:
            self.load_model()
        if self._model is None:
            return [0.0] * 384   # stub: all-MiniLM-L6-v2 outputs 384 dims
        return self._model.encode(text, normalize_embeddings=True).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self._loaded:
            self.load_model()
        if self._model is None:
            return [[0.0] * 384 for _ in texts]
        return self._model.encode(texts, normalize_embeddings=True).tolist()


embedding_service = EmbeddingService()
