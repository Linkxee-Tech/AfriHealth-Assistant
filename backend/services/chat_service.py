"""
Chat service — orchestrates RAG engine, LLM engine, and Hybrid Orchestrator.
Routes call this; service calls core.
"""

import time
import json
from typing import Dict, Generator, List

from backend.core.rag_engine import rag_engine
from backend.core.llm_engine import llm_engine
from backend.core.embedding_service import embedding_service
from backend.core.hybrid_orchestrator import hybrid_orchestrator
from backend.core.prompt_templates import build_rag_prompt, get_system_prompt
from backend.core.gemini_integration import gemini_client
from backend.database.db_manager import db_manager
from backend.utils.logger import get_logger
from backend.utils.helpers import generate_session_id, now_str

try:
    from langdetect import detect
except ImportError:
    detect = None

logger = get_logger(__name__)

# Map ISO language codes from langdetect to our supported languages
LANG_MAP = {
    "ha": "Hausa",
    "sw": "Swahili",
    "yo": "Yoruba",
    "ig": "Igbo",
    "fr": "French",
    "en": "English",
}

def _detect_language(query: str, fallback: str) -> str:
    """Auto-detect language of user query and map it to supported languages."""
    if detect:
        try:
            lang_code = detect(query)
            if lang_code in LANG_MAP:
                return LANG_MAP[lang_code]
        except Exception:
            pass
    return fallback


def _ensure_rag_ready():
    """Wire dependencies into RAG engine on first call."""
    if rag_engine._llm is None:
        rag_engine.set_llm(llm_engine)
    if rag_engine._embedder is None:
        rag_engine.set_embedder(embedding_service)
    if not rag_engine._initialized:
        rag_engine.initialize()


def _use_gemini_generate(full_prompt: str, system_prompt: str) -> str:
    """Call Gemini cloud and return the full answer string."""
    return gemini_client.generate(full_prompt, system_instruction=system_prompt)


def _use_gemini_stream(full_prompt: str, system_prompt: str) -> Generator[str, None, None]:
    """Call Gemini cloud and stream back text chunks."""
    yield from gemini_client.stream_generate(full_prompt, system_instruction=system_prompt)


class ChatService:
    def generate_response(
        self,
        query: str,
        language: str = "English",
        session_id: str = None,
        top_k: int = 5,
        detail_level: str = "Standard",
        hybrid: bool = True
    ) -> Dict:
        """Blocking chat — returns full answer + sources + metadata."""
        _ensure_rag_ready()
        t0 = time.perf_counter()
        
        # Auto-detect language
        detected_language = _detect_language(query, fallback=language)

        if hybrid:
            ctx = hybrid_orchestrator.prepare_context(query, top_k)
            context_str = ctx["context_str"]
            sources = ctx["sources"]
            mode = ctx["mode"]
        else:
            result = rag_engine.generate_answer(query, language=detected_language, top_k=top_k)
            return {
                "answer": result["answer"],
                "sources": result["sources"],
                "mode": "OFFLINE",
                "session_id": session_id or generate_session_id(),
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
                "query": query,
                "language": detected_language,
                "knowledge_base_hits": rag_engine.get_collection_count()
            }

        system_prompt = get_system_prompt(detected_language)
        rag_prompt = build_rag_prompt(query, context_str, detail_level)
        full_prompt = f"{rag_prompt}"   # system_instruction is passed separately

        if not llm_engine._loaded:
            llm_engine.load_model()

        # Decide whether to use local LLM or Gemini cloud
        use_cloud = llm_engine._model is None  # no local model loaded
        if not use_cloud and hybrid_orchestrator.is_online() and mode in ["ONLINE", "HYBRID_EMERGENCY"]:
            use_cloud = True  # prefer cloud for these modes too

        answer = ""
        if use_cloud and gemini_client.is_configured:
            try:
                answer = _use_gemini_generate(full_prompt, system_prompt)
            except Exception:
                logger.exception("Cloud AI (Gemini) fallback failed — falling back to stub")
                answer = llm_engine.generate(full_prompt)
        else:
            answer = llm_engine.generate(full_prompt)

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        return {
            "answer": answer,
            "sources": sources,
            "mode": mode,
            "session_id": session_id or generate_session_id(),
            "elapsed_ms": elapsed_ms,
            "query": query,
            "language": language,
            "knowledge_base_hits": rag_engine.get_collection_count()
        }

    def stream_response(
        self,
        query: str,
        language: str = "English",
        session_id: str = None,
        top_k: int = 5,
        detail_level: str = "Standard",
        hybrid: bool = True
    ) -> Generator[str, None, None]:
        """Streaming chat."""
        _ensure_rag_ready()
        
        # Auto-detect language
        detected_language = _detect_language(query, fallback=language)

        if hybrid:
            ctx = hybrid_orchestrator.prepare_context(query, top_k)
            context_str = ctx["context_str"]
            sources = ctx["sources"]
            mode = ctx["mode"]
        else:
            ctx = rag_engine.retrieve_context(query, top_k)
            context_str = ctx["context_str"]
            sources = ctx["sources"]
            mode = "OFFLINE"

        # Emit the first chunk with JSON sources
        yield f"__SOURCES__:{json.dumps(sources)}\n"

        system_prompt = get_system_prompt(detected_language)
        rag_prompt = build_rag_prompt(query, context_str, detail_level)
        full_prompt = f"{rag_prompt}"

        if not llm_engine._loaded:
            llm_engine.load_model()

        use_cloud = llm_engine._model is None
        if not use_cloud and hybrid_orchestrator.is_online() and mode in ["ONLINE", "HYBRID_EMERGENCY"]:
            use_cloud = True

        if use_cloud and gemini_client.is_configured:
            try:
                yield from _use_gemini_stream(full_prompt, system_prompt)
                return
            except Exception:
                logger.exception("Cloud AI (Gemini) streaming failed — falling back to local LLM stub")

        # Local LLM (or stub if model file absent)
        yield from llm_engine.stream_generate(full_prompt)

    def save_conversation(self, messages: List[Dict], session_id: str = None, user_id: int = None) -> str:
        """Persist a conversation to SQLite."""
        return db_manager.save_conversation(messages, session_id=session_id, user_id=user_id)

    def process_message(self, query: str, **kwargs) -> Dict:
        return self.generate_response(query, **kwargs)

    def process_stream(self, query: str, **kwargs) -> Generator[str, None, None]:
        yield from self.stream_response(query, **kwargs)

    @staticmethod
    def format_response(result: Dict) -> Dict:
        return {"answer": str(result.get("answer", "")), "sources": result.get("sources", []), "mode": result.get("mode", "OFFLINE"), "elapsed_ms": result.get("elapsed_ms", 0.0), "session_id": result.get("session_id", "")}


chat_service = ChatService()
