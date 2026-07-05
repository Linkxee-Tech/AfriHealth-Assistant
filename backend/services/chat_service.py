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
        hybrid: bool = True
    ) -> Dict:
        """Blocking chat — returns full answer + sources + metadata."""
        _ensure_rag_ready()
        t0 = time.perf_counter()
        
        if hybrid:
            ctx = hybrid_orchestrator.prepare_context(query, top_k)
            context_str = ctx["context_str"]
            sources = ctx["sources"]
            mode = ctx["mode"]
            
            system_prompt = get_system_prompt(language)
            rag_prompt = build_rag_prompt(query, context_str)
            full_prompt = f"{system_prompt}\n\n{rag_prompt}"
            
            if not llm_engine._loaded:
                llm_engine.load_model()
            
            use_cloud = False
            if hybrid_orchestrator.is_online():
                if mode in ["ONLINE", "HYBRID_EMERGENCY"]:
                    use_cloud = True
                elif llm_engine._model is None:
                    use_cloud = True
            
            if use_cloud:
                import os
                api_key = os.getenv("GOOGLE_API_KEY", "")
                if api_key:
                    try:
                        import google.generativeai as generativeai
                        generativeai.configure(api_key=api_key)
                        # Simple non-streaming generation via Gemini
                        resp = generativeai.generate_text(model="gemini-1.0", prompt=full_prompt)
                        # `resp` may expose text as `resp.text` or str(resp)
                        answer = getattr(resp, "text", str(resp))
                    except Exception as e:
                        logger.exception("Cloud AI Fallback failed")
                        answer = llm_engine.generate(full_prompt)
                else:
                    answer = llm_engine.generate(full_prompt)
            else:
                answer = llm_engine.generate(full_prompt)
        else:
            result = rag_engine.generate_answer(query, language=language, top_k=top_k)
            answer = result["answer"]
            sources = result["sources"]
            mode = "OFFLINE"
            
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
        top_k: int = 3,
        hybrid: bool = True
    ) -> Generator[str, None, None]:
        """Streaming chat — yields tokens directly for FastAPI StreamingResponse."""
        _ensure_rag_ready()
        
        if not hybrid:
            for token in rag_engine.stream_answer(query, language=language, top_k=top_k):
                yield token
            return

        ctx = hybrid_orchestrator.prepare_context(query, top_k)
        context_str = ctx["context_str"]
        sources = ctx["sources"]
        mode = ctx.get("mode", "HYBRID")
        
        system_prompt = get_system_prompt(language)
        rag_prompt = build_rag_prompt(query, context_str)
        full_prompt = f"{system_prompt}\n\n{rag_prompt}"
        
        # Yield sources as a JSON header line (frontend can parse it)
        yield f"__SOURCES__:{json.dumps(sources)}\n"
        
        if not llm_engine._loaded:
            llm_engine.load_model()

        # Cloud AI Fallback
        use_cloud = False
        if hybrid_orchestrator.is_online():
            if mode in ["ONLINE", "HYBRID_EMERGENCY"]:
                use_cloud = True
            elif llm_engine._model is None:
                use_cloud = True

        if use_cloud:
            try:
                import os
                api_key = os.getenv("GOOGLE_API_KEY", "")
                if api_key:
                    import google.generativeai as generativeai
                    generativeai.configure(api_key=api_key)
                    resp = generativeai.generate_text(model="gemini-1.0", prompt=full_prompt)
                    answer = getattr(resp, "text", str(resp))
                    # Yield the full response as a single chunk for streaming endpoint
                    yield answer
                    return
                else:
                    yield "(Cloud AI requested but GOOGLE_API_KEY is missing. Falling back to Local LLM...)\n\n"
            except Exception as e:
                logger.exception("Cloud AI Fallback failed during streaming")
                yield "(Cloud AI Fallback failed: cloud provider error or quota exceeded. Falling back to Local LLM...)\n\n"
        
        for token in llm_engine.stream_generate(full_prompt):
            yield token


    def save_conversation(self, messages: List[Dict], session_id: str = None, user_id: int = None) -> str:
        """Persist a conversation to SQLite."""
        return db_manager.save_conversation(messages, session_id=session_id, user_id=user_id)


chat_service = ChatService()
