"""
RAG Engine — LangChain + ChromaDB + local embeddings.

Pipeline:
  query → embed → ChromaDB similarity search → build prompt → LLM → answer

Falls back to direct LLM generation (no retrieval) when ChromaDB is not
available or the knowledge base is empty.
"""

import json
from pathlib import Path
from typing import List, Dict, Generator, Optional

from backend.config import settings
from backend.utils.logger import get_logger
from backend.core.prompt_templates import build_rag_prompt, get_system_prompt

logger = get_logger(__name__)

_CHROMA_AVAILABLE = False
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    _CHROMA_AVAILABLE = True
except ImportError:
    logger.warning("chromadb not installed - RAG running in LLM-only mode.")

_LANGCHAIN_AVAILABLE = False
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    _LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("langchain not installed - using built-in chunking.")


class RAGEngine:
    """Manages the full retrieval-augmented generation pipeline."""

    COLLECTION_NAME = "afrihealth_knowledge"

    def __init__(
        self,
        vector_db_path: str = None,
        llm_engine=None,
        embedding_service=None,
    ):
        self.vector_db_path   = vector_db_path or settings.VECTOR_DB_PATH
        self._llm             = llm_engine
        self._embedder        = embedding_service
        self._chroma_client   = None
        self._collection      = None
        self._initialized     = False

    # ------------------------------------------------------------------
    # Lazy inject dependencies (avoids circular imports)
    # ------------------------------------------------------------------
    def set_llm(self, llm_engine):
        self._llm = llm_engine

    def set_embedder(self, embedding_service):
        self._embedder = embedding_service

    # ------------------------------------------------------------------
    def initialize(self):
        if self._initialized:
            return
        if not _CHROMA_AVAILABLE:
            logger.warning("ChromaDB unavailable - RAG in LLM-only mode.")
            self._initialized = True
            return
        try:
            Path(self.vector_db_path).mkdir(parents=True, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(
                path=self.vector_db_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._chroma_client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "RAG engine initialised - %d documents in knowledge base.",
                self._collection.count(),
            )
        except Exception as exc:
            logger.error("RAG init error: %s", exc)
        self._initialized = True

    # ------------------------------------------------------------------
    def retrieve(self, query: str, top_k: int = 3, user_id: int | None = None) -> List[Dict]:
        """Retrieve the top-k most relevant document chunks for a query."""
        if not self._initialized:
            self.initialize()
        if self._collection is None or self._embedder is None:
            return []
        try:
            query_embedding = self._embedder.embed(query)
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=self._collection.count() or 1,
                include=["documents", "metadatas", "distances"],
            )
            chunks = []
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                if meta.get("visibility") == "private" and str(meta.get("user_id")) != str(user_id):
                    continue
                chunks.append({
                    "text": doc,
                    "source": meta.get("source", "Unknown"),
                    "chunk_id": meta.get("chunk_id", ""),
                    "relevance_score": round(1 - dist, 4),
                })
                if len(chunks) == top_k:
                    break
            return chunks
        except Exception as exc:
            logger.error("RAG retrieval error: %s", exc)
            return []

    # ------------------------------------------------------------------
    def generate_answer(
        self,
        query: str,
        language: str = "English",
        top_k: int = 3,
        user_id: Optional[int] = None,
    ) -> Dict:
        """Blocking RAG answer. Returns answer + sources dict."""
        if not self._initialized:
            self.initialize()
        if self._llm is None:
            return {"answer": "[LLM not set on RAG engine]", "sources": []}

        chunks = self.retrieve(query, top_k=top_k, user_id=user_id)
        context = "\n\n".join(
            f"[Source: {c['source']}]\n{c['text']}" for c in chunks
        )
        system_prompt = get_system_prompt(language)
        rag_prompt    = build_rag_prompt(query, context)
        full_prompt   = f"{system_prompt}\n\n{rag_prompt}"

        answer  = self._llm.generate(full_prompt)
        sources = list({c["source"] for c in chunks})
        return {"answer": answer, "sources": sources}

    # ------------------------------------------------------------------
    def stream_answer(
        self,
        query: str,
        language: str = "English",
        top_k: int = 3,
        user_id: Optional[int] = None,
    ) -> Generator[str, None, None]:
        """Streaming RAG answer - yields text tokens."""
        if not self._initialized:
            self.initialize()
        if self._llm is None:
            yield "[LLM not set on RAG engine]"
            return

        chunks = self.retrieve(query, top_k=top_k, user_id=user_id)
        context = "\n\n".join(
            f"[Source: {c['source']}]\n{c['text']}" for c in chunks
        )
        system_prompt = get_system_prompt(language)
        rag_prompt    = build_rag_prompt(query, context)
        full_prompt   = f"{system_prompt}\n\n{rag_prompt}"

        # First yield sources as a JSON header line (frontend can parse it)
        sources = list({c["source"] for c in chunks})
        yield f"__SOURCES__:{json.dumps(sources)}\n"

        for token in self._llm.stream_generate(full_prompt):
            yield token

    # ------------------------------------------------------------------
    def add_documents(self, documents: List[Dict]) -> int:
        """
        Add chunked documents to the ChromaDB vector store.

        Each document dict: {"text": str, "source": str, "chunk_id": str/int}
        Returns number of chunks added.
        """
        if not self._initialized:
            self.initialize()
        if self._collection is None or self._embedder is None:
            logger.warning("Cannot add documents — collection or embedder not available.")
            return 0
        try:
            texts      = [d["text"] for d in documents]
            embeddings = self._embedder.embed_batch(texts)
            ids = [
                f"{d.get('metadata', {}).get('user_id', 'global')}::{d.get('source', 'doc')}_{d.get('chunk_id', i)}"
                for i, d in enumerate(documents)
            ]
            metadatas = [
                {
                    "source": d.get("source", "Unknown"),
                    "chunk_id": str(d.get("chunk_id", i)),
                    **d.get("metadata", {}),
                }
                for i, d in enumerate(documents)
            ]
            batch_size = 4000
            for start in range(0, len(documents), batch_size):
                end = start + batch_size
                self._collection.upsert(
                    ids=ids[start:end],
                    embeddings=embeddings[start:end],
                    documents=texts[start:end],
                    metadatas=metadatas[start:end],
                )
            logger.info("Added %d chunks to knowledge base.", len(documents))
            return len(documents)
        except Exception as exc:
            logger.error("Error adding documents to RAG: %s", exc)
            return 0

    def get_collection_count(self) -> int:
        if self._collection is None:
            return 0
        return self._collection.count()


rag_engine = RAGEngine()
