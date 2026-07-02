"""
Knowledge Base Builder — orchestrates the full RAG knowledge base pipeline:
  load raw docs → extract text → chunk → embed → store in ChromaDB

Run standalone:
  python -m knowledge_base.builder
Or via script:
  python scripts/build_knowledge_base.py
"""

import json
import time
from pathlib import Path
from typing import List, Dict

from backend.config import settings
from backend.utils.logger import get_logger
from knowledge_base.data_loader import DataLoader, data_loader
from knowledge_base.text_splitter import TextSplitter, text_splitter
from knowledge_base.embedder import Embedder, embedder
from knowledge_base.vector_store import VectorStore, vector_store

logger = get_logger(__name__)

PROCESSED_DATA_PATH = Path(settings.VECTOR_DB_PATH).parent.parent / "processed_data"


class KnowledgeBaseBuilder:
    """Full pipeline: raw docs → ChromaDB vector store."""

    def __init__(
        self,
        loader:   DataLoader  = None,
        splitter: TextSplitter = None,
        emb:      Embedder    = None,
        store:    VectorStore  = None,
    ):
        self.loader   = loader   or data_loader
        self.splitter = splitter or text_splitter
        self.emb      = emb      or embedder
        self.store    = store    or vector_store

    # ------------------------------------------------------------------
    def load_datasets(self) -> List[Dict]:
        logger.info("Step 1/4 — Loading datasets from raw_data/ …")
        return self.loader.load_all()

    def chunk_documents(self, raw_files: List[Dict]) -> List[Dict]:
        """Step 2: Extract text and split into chunks."""
        logger.info("Step 2/4 — Extracting text and chunking %d files …", len(raw_files))
        from backend.core.document_processor import document_processor

        all_chunks: List[Dict] = []
        for f in raw_files:
            try:
                processed = document_processor.process_document(
                    file_bytes=f["bytes"], filename=f["filename"]
                )
                chunks = self.splitter.split(
                    processed["raw_text"],
                    source=f"{f['source_dir']}/{f['filename']}",
                )
                all_chunks.extend(chunks)
                logger.info(
                    "  %s → %d chunks", f["filename"], len(chunks)
                )
            except Exception as exc:
                logger.error("  Failed %s: %s", f["filename"], exc)

        logger.info("Total chunks: %d", len(all_chunks))
        return all_chunks

    def generate_embeddings(self, chunks: List[Dict]) -> List[Dict]:
        logger.info("Step 3/4 — Generating embeddings for %d chunks …", len(chunks))
        return self.emb.embed_chunks(chunks)

    def store_vectors(self, chunks: List[Dict]) -> int:
        logger.info("Step 4/4 — Storing vectors in ChromaDB …")
        self.store.connect()
        n = self.store.upsert(chunks)
        logger.info("Knowledge base complete. %d vectors stored.", n)
        return n

    def _save_processed_metadata(self, chunks: List[Dict]):
        """Persist chunk metadata to processed_data/ for auditing."""
        PROCESSED_DATA_PATH.mkdir(parents=True, exist_ok=True)
        meta_only = [
            {"source": c["source"], "chunk_id": c["chunk_id"], "text_len": len(c["text"])}
            for c in chunks
        ]
        with open(PROCESSED_DATA_PATH / "metadata.json", "w") as f:
            json.dump({"total_chunks": len(chunks), "chunks": meta_only}, f, indent=2)
        logger.info("Metadata saved to processed_data/metadata.json")

    def build(self) -> Dict:
        """Execute the full pipeline. Returns a summary dict."""
        t0 = time.perf_counter()
        logger.info("=== AfriHealth Knowledge Base Build Started ===")

        raw_files = self.load_datasets()
        if not raw_files:
            logger.warning("No raw documents found. Place PDFs/TXTs in backend/data/raw_data/")
            return {"status": "no_data", "chunks": 0, "elapsed_s": 0}

        chunks    = self.chunk_documents(raw_files)
        chunks    = self.generate_embeddings(chunks)
        self._save_processed_metadata(chunks)
        stored    = self.store_vectors(chunks)

        elapsed   = round(time.perf_counter() - t0, 1)
        summary   = {
            "status":     "success",
            "files":      len(raw_files),
            "chunks":     len(chunks),
            "stored":     stored,
            "elapsed_s":  elapsed,
        }
        logger.info("=== Build complete: %s ===", summary)
        return summary


if __name__ == "__main__":
    builder = KnowledgeBaseBuilder()
    result  = builder.build()
    print(result)
