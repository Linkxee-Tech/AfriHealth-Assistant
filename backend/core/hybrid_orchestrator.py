import time
import requests
from typing import Dict, Any, List

from backend.config import settings
from backend.utils.logger import get_logger
from backend.core.rag_engine import rag_engine

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

logger = get_logger(__name__)

class HybridOrchestrator:
    """
    Orchestrates between offline and online capabilities.
    Decides when to use local vs. cloud resources and integrates live web search.
    """
    def __init__(self):
        self.rag_engine = rag_engine
        self._cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
        self._request_times: List[float] = []
        self.cache_ttl_seconds = 300
        self.max_requests_per_minute = 30

    def is_online(self) -> bool:
        """Check if internet connection is available."""
        # For demonstration or local dev, always allow hybrid if duckduckgo is installed
        if not DDGS_AVAILABLE:
            return False
        try:
            requests.get("https://duckduckgo.com", timeout=2)
            return True
        except requests.RequestException:
            return False

    def is_simple_query(self, query: str) -> bool:
        """Determine if query can be handled locally without online search."""
        simple_keywords = ['symptom', 'fever', 'cough', 'headache', 'medicine', 'treatment', 'malaria', 'typhoid', 'hello', 'hi']
        return any(keyword in query.lower() for keyword in simple_keywords)
        
    def is_emergency_query(self, query: str) -> bool:
        emergency_keywords = ['emergency', 'heart attack', 'stroke', 'bleeding', 'unconscious', 'poison', 'suicide']
        return any(keyword in query.lower() for keyword in emergency_keywords)
        
    def has_medical_terms(self, query: str) -> bool:
        medical_terms = ['syndrome', 'disease', 'virus', 'bacteria', 'infection', 'chronic', 'acute', 'therapy']
        return any(term in query.lower() for term in medical_terms)
        
    def is_research_query(self, query: str) -> bool:
        research_terms = ['latest', 'research', 'study', 'outbreak', 'news', 'statistics', 'update']
        return any(term in query.lower() for term in research_terms)
        
    def decide_processing_mode(self, query: str) -> str:
        """
        Decide whether to use offline, online, or hybrid mode.
        """
        if not self.is_online():
            return "OFFLINE"
        if self.is_simple_query(query):
            return "OFFLINE"
        if self.is_emergency_query(query):
            return "HYBRID_EMERGENCY"
        if self.has_medical_terms(query):
            return "HYBRID"
        if self.is_research_query(query):
            return "ONLINE"
        return "HYBRID"

    def search_online(self, query: str, limit: int = 3) -> List[Dict[str, str]]:
        """Perform a quick online search using DuckDuckGo."""
        if not DDGS_AVAILABLE:
            return []
        now = time.monotonic()
        self._request_times = [stamp for stamp in self._request_times if now - stamp < 60]
        if len(self._request_times) >= self.max_requests_per_minute:
            logger.warning("Online search rate limit reached")
            return []
        self._request_times.append(now)
        
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=limit))
                return [{"content": r.get("body", ""), "source": r.get("href", "")} for r in results]
        except Exception as e:
            logger.error("Web search failed: %s", e)
            return []

    def prepare_context(self, query: str, top_k: int = 3, user_id: int | None = None) -> Dict[str, Any]:
        """
        Entry point to process a user query using the best available resources.
        Returns the combined context string and sources list.
        """
        cache_key = f"{user_id}::{query.strip().lower()}::{top_k}"
        cached = self._cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < self.cache_ttl_seconds:
            return {**cached[1], "cached": True}
        mode = self.decide_processing_mode(query)
        
        if mode == "OFFLINE":
            result = self._prepare_offline(query, top_k, user_id=user_id)
            self._cache[cache_key] = (time.monotonic(), result)
            return result
            
        local_chunks = self.rag_engine.retrieve(query, top_k=top_k, user_id=user_id) if mode != "ONLINE" else []
        
        result = self._prepare_hybrid(query, top_k, local_chunks)
        self._cache[cache_key] = (time.monotonic(), result)
        return result

    def decide_mode(self, query: str) -> str:
        return self.decide_processing_mode(query)

    def process_offline(self, query: str, top_k: int = 3, user_id: int | None = None) -> Dict[str, Any]:
        return self._prepare_offline(query, top_k, user_id=user_id)

    def process_hybrid(self, query: str, top_k: int = 3, user_id: int | None = None) -> Dict[str, Any]:
        return self._prepare_hybrid(query, top_k, self.rag_engine.retrieve(query, top_k=top_k, user_id=user_id))

    def combine_contexts(self, local_chunks: List[Dict[str, Any]], web_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"context_str": "\n\n".join([*(c.get("text", "") for c in local_chunks), *(r.get("content", "") for r in web_results)]), "sources": [*(c.get("source", "") for c in local_chunks), *(r.get("source", "") for r in web_results)]}

    def process_query(self, query: str, top_k: int = 3, user_id: int | None = None) -> Dict[str, Any]:
        return self.prepare_context(query, top_k, user_id=user_id)
        
    def _prepare_offline(self, query: str, top_k: int, pre_fetched=None, user_id: int | None = None) -> Dict[str, Any]:
        """Prepare context solely from offline RAG."""
        chunks = pre_fetched if pre_fetched is not None else self.rag_engine.retrieve(query, top_k=top_k, user_id=user_id)
        context = "\n\n".join(f"[Source: {c['source']}]\n{c['text']}" for c in chunks) if chunks else "No specific offline knowledge found."
        sources = list(set([c['source'] for c in chunks])) if chunks else []
        return {
            "mode": "OFFLINE",
            "context_str": context,
            "sources": sources
        }

    def _prepare_hybrid(self, query: str, top_k: int, local_chunks) -> Dict[str, Any]:
        """Prepare context by combining offline RAG and online Web Search."""
        local_str = "\n\n".join(f"[Source: {c['source']}]\n{c['text']}" for c in local_chunks) if local_chunks else ""
        local_sources = [c['source'] for c in local_chunks] if local_chunks else []
        
        web_results = self.search_online(query, limit=3)
        web_str = "\n\n".join([f"[Source: {r['source']}]\n{r['content']}" for r in web_results])
        web_sources = [r["source"] for r in web_results]
        
        combined_context = f"--- OFFLINE MEDICAL KNOWLEDGE ---\n{local_str}\n\n--- ONLINE WEB SEARCH (CURRENT) ---\n{web_str}"
        combined_sources = list(set(local_sources + web_sources))
        
        return {
            "mode": "HYBRID",
            "context_str": combined_context,
            "sources": combined_sources
        }

# Singleton instance
hybrid_orchestrator = HybridOrchestrator()
