"""Document service — processes uploads and stores results."""

from typing import Dict
from backend.core.document_processor import document_processor
from backend.core.rag_engine import rag_engine
from backend.core.embedding_service import embedding_service
from backend.database.db_manager import db_manager
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentService:
    def process_and_store(self, file_bytes: bytes, filename: str) -> Dict:
        """
        Full pipeline:
          1. Extract text (OCR / PDF / DOCX / TXT)
          2. Chunk the text
          3. Add chunks to the RAG knowledge base
          4. Persist document record to SQLite
          5. Return result dict
        """
        logger.info("Processing document: %s", filename)
        result = document_processor.process_document(file_bytes, filename)

        # Add chunks to RAG
        chunks_added = 0
        if result["chunks"] and rag_engine._initialized:
            docs_to_add = [
                {"text": c["text"], "source": filename, "chunk_id": c["chunk_id"]}
                for c in result["chunks"]
            ]
            chunks_added = rag_engine.add_documents(docs_to_add)

        # Generate a short AI analysis summary (stub for now)
        analysis = (
            f"Document '{filename}' processed successfully. "
            f"{len(result['raw_text'])} characters extracted, "
            f"{result['chunk_count']} chunks added to knowledge base."
        )

        # Persist to SQLite
        doc_id = db_manager.save_document(
            filename=filename,
            file_type=result["file_type"],
            content=result["raw_text"][:5000],   # store first 5k chars
            analysis_result=analysis,
        )

        return {
            "doc_id": doc_id,
            "filename": filename,
            "file_type": result["file_type"],
            "char_count": len(result["raw_text"]),
            "chunk_count": result["chunk_count"],
            "chunks_added_to_rag": chunks_added,
            "extracted_text_preview": result["raw_text"][:500],
            "analysis": analysis,
        }


document_service = DocumentService()
