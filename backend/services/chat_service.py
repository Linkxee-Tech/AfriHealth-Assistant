"""
Chat service — orchestrates RAG engine + LLM engine for chat handling.
Routes call this; service calls core. Nothing else should call core directly.
"""

import time
from typing import Dict, Generator, List

from backend.core.rag_engine import rag_engine
from backend.core.llm_engine import llm_engine
from backend.core.embedding_service import embedding_service
from backend.database.db_manager import db_manager
from backend.utils.logger import get_logger
from backend.utils.helpers import generate_session_id, now_str

logger = get_logger(__name__)


def _ensure_rag_ready():
    """Wire dependencies into RAG engine on first call."""
    if rag_engine._llm is None:
        rag_engine.set_llm(llm_engine)
    if rag_engine._embedder is None:
        rag_engine.set_embedder(embedding_service)
    if not rag_engine._initialized:
        rag_engine.initialize()


class ChatService:
    def generate_response(
        self,
        query: str,
        language: str = "English",
        session_id: str = None,
        top_k: int = 3,
    ) -> Dict:
        """Blocking chat — returns full answer + sources + metadata."""
        _ensure_rag_ready()
        t0 = time.perf_counter()
        result = rag_engine.generate_answer(query, language=language, top_k=top_k)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        result["session_id"]   = session_id or generate_session_id()
        result["elapsed_ms"]   = elapsed_ms
        result["query"]        = query
        result["language"]     = language
        result["knowledge_base_hits"] = rag_engine.get_collection_count()
        return result

    def stream_response(
        self,
        query: str,
        language: str = "English",
        top_k: int = 3,
    ) -> Generator[str, None, None]:
        """Streaming chat — yields tokens directly for FastAPI StreamingResponse."""
        _ensure_rag_ready()
        for token in rag_engine.stream_answer(query, language=language, top_k=top_k):
            yield token

    def save_conversation(self, messages: List[Dict], session_id: str = None) -> str:
        """Persist a conversation to SQLite."""
        return db_manager.save_conversation(messages, session_id=session_id)


chat_service = ChatService()
