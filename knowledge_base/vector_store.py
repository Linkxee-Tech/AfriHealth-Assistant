"""
Vector Store — persists embedded chunks into ChromaDB.
Separate from the RAG engine so the knowledge base can be
rebuilt offline independently of the running API server.
"""

from typing import List, Dict
from pathlib import Path
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    _CHROMA_OK = True
except ImportError:
    _CHROMA_OK = False
    logger.warning("chromadb not installed - vector store unavailable.")

COLLECTION_NAME = "afrihealth_knowledge"
CHROMA_BATCH_SIZE = 4000


class VectorStore:
    def __init__(self, db_path: str = None):
        self.db_path    = db_path or settings.VECTOR_DB_PATH
        self._client    = None
        self._collection = None

    def connect(self):
        if not _CHROMA_OK:
            logger.error("chromadb not available.")
            return
        Path(self.db_path).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=self.db_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("VectorStore connected. Existing docs: %d", self._collection.count())

    def upsert(self, chunks: List[Dict]) -> int:
        """
        Upsert chunks with pre-computed embeddings into ChromaDB.
        Each chunk dict must have: text, source, chunk_id, embedding.
        """
        if self._collection is None:
            self.connect()
        if self._collection is None:
            return 0

        ids        = [f"{c['source']}_{c['chunk_id']}" for c in chunks]
        embeddings = [c["embedding"] for c in chunks]
        documents  = [c["text"] for c in chunks]
        metadatas  = [{"source": c["source"], "chunk_id": str(c["chunk_id"])} for c in chunks]

        for start in range(0, len(chunks), CHROMA_BATCH_SIZE):
            end = start + CHROMA_BATCH_SIZE
            self._collection.upsert(
                ids=ids[start:end],
                embeddings=embeddings[start:end],
                documents=documents[start:end],
                metadatas=metadatas[start:end],
            )
        logger.info("Upserted %d chunks.", len(chunks))
        return len(chunks)

    def count(self) -> int:
        if self._collection is None:
            return 0
        return self._collection.count()

    def clear(self):
        if self._client and _CHROMA_OK:
            self._client.delete_collection(COLLECTION_NAME)
            self._collection = self._client.create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("Knowledge base cleared.")


vector_store = VectorStore()
