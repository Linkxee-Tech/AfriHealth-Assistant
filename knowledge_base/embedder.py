"""
Embedder - generates vector embeddings for document chunks.
Thin wrapper around EmbeddingService with batch processing and progress logging.
"""

from typing import List, Dict
from backend.core.embedding_service import EmbeddingService, embedding_service
from backend.utils.logger import get_logger

logger = get_logger(__name__)

BATCH_SIZE = 64


class Embedder:
    def __init__(self, service: EmbeddingService = None):
        self._service = service or embedding_service

    def embed_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Add 'embedding' key to each chunk dict.
        Processes in batches to manage memory.
        """
        if not self._service._loaded:
            self._service.load_model()

        total = len(chunks)
        logger.info("Embedding %d chunks in batches of %d ...", total, BATCH_SIZE)

        for batch_start in range(0, total, BATCH_SIZE):
            batch = chunks[batch_start: batch_start + BATCH_SIZE]
            texts = [c["text"] for c in batch]
            vectors = self._service.embed_batch(texts)
            for chunk, vec in zip(batch, vectors):
                chunk["embedding"] = vec
            logger.info(
                "Embedded batch %d/%d",
                min(batch_start + BATCH_SIZE, total),
                total,
            )

        return chunks


embedder = Embedder()
