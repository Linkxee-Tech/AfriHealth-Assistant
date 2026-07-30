"""Embedding service with a local transformer and deterministic offline fallback."""

from pathlib import Path
import hashlib
import math
import re
from typing import List

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_EMBEDDINGS_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    _EMBEDDINGS_AVAILABLE = True
except ImportError:
    logger.warning("sentence-transformers not installed — using hash embeddings.")


class EmbeddingService:
    def __init__(self, model_path: str = None):
        self.model_path = model_path or settings.EMBEDDING_MODEL
        self._model = None
        self._loaded = False
        self._mode = "unloaded"
        self._load_error = None

    def load_model(self):
        if self._loaded:
            return self._model is not None
        if not _EMBEDDINGS_AVAILABLE:
            self._mode = "hash"
            self._load_error = "sentence-transformers is not installed"
            self._loaded = True
            return False
        try:
            model_path = Path(self.model_path)
            if not model_path.exists():
                raise FileNotFoundError(f"Local embedding model not found: {self.model_path}")
            logger.info("Loading embedding model from %s ...", self.model_path)
            self._model = SentenceTransformer(str(model_path))
            self._mode = "sentence-transformer"
            self._loaded = True
            logger.info("Embedding model loaded.")
            return True
        except Exception as exc:
            logger.error("Failed to load embedding model: %s", exc)
            self._load_error = str(exc)
            self._mode = "hash"
            self._loaded = True
            return False

    def embed(self, text: str) -> List[float]:
        if not self._loaded:
            self.load_model()
        if self._model is None:
            return self._hash_embedding(text)
        return self._model.encode(text, normalize_embeddings=True).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self._loaded:
            self.load_model()
        if self._model is None:
            return [self._hash_embedding(text) for text in texts]
        return self._model.encode(texts, normalize_embeddings=True).tolist()

    @staticmethod
    def _hash_embedding(text: str, dimensions: int = 384) -> List[float]:
        """Deterministic lexical vectors for fully offline retrieval fallback."""
        vector = [0.0] * dimensions
        tokens = re.findall(r"[a-z0-9]{2,}", (text or "").lower())
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % dimensions
            vector[index] += 1.0 if digest[4] & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    def get_status(self) -> dict:
        return {
            "loaded": self._loaded,
            "mode": self._mode,
            "model_path": self.model_path,
            "load_error": self._load_error,
        }


embedding_service = EmbeddingService()
