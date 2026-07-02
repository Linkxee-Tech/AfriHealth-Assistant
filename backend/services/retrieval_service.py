"""Retrieval service — exposes RAG document retrieval."""

from typing import List, Dict
from backend.core.rag_engine import rag_engine
from backend.core.embedding_service import embedding_service
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class RetrievalService:
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        if not rag_engine._initialized:
            rag_engine.set_embedder(embedding_service)
            rag_engine.initialize()
        return rag_engine.retrieve(query, top_k=top_k)

    def add_documents(self, documents: List[Dict]) -> int:
        if not rag_engine._initialized:
            rag_engine.set_embedder(embedding_service)
            rag_engine.initialize()
        return rag_engine.add_documents(documents)

    def knowledge_base_size(self) -> int:
        return rag_engine.get_collection_count()


retrieval_service = RetrievalService()
