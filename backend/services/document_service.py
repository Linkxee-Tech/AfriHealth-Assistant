"""Document service — processes uploads and stores results."""

from typing import Dict
from backend.core.document_processor import document_processor
from backend.core.rag_engine import rag_engine
from backend.core.embedding_service import embedding_service
from backend.database.db_manager import db_manager
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentService:
    def process_and_store(self, file_bytes: bytes, filename: str, user_id: int = None, patient_id: int = None) -> Dict:
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
        if result["chunks"]:
            if rag_engine._llm is None:
                from backend.core.llm_engine import llm_engine
                rag_engine.set_llm(llm_engine)
            if rag_engine._embedder is None:
                rag_engine.set_embedder(embedding_service)
            if not rag_engine._initialized:
                rag_engine.initialize()

            # Create metadata dict
            metadata = {"source": filename, "visibility": "private"}
            if user_id is not None:
                metadata["user_id"] = user_id
            if patient_id is not None:
                metadata["patient_id"] = patient_id

            docs_to_add = [
                {
                    "text": c["text"],
                    "source": metadata["source"],
                    "chunk_id": c["chunk_id"],
                    "metadata": metadata,
                }
                for c in result["chunks"]
            ]
            chunks_added = rag_engine.add_documents(docs_to_add)

        # Use the configured local/cloud model when available. If neither is
        # available, return an explicit extraction-only result rather than a
        # fabricated clinical interpretation.
        analysis = ""
        try:
            from backend.core.llm_engine import llm_engine
            from backend.core.gemini_integration import gemini_client
            excerpt = result["raw_text"][:6000]
            prompt = (
                "Summarise this medical document for a clinician. Do not diagnose, "
                "do not invent findings, and state when information is missing.\n\n"
                f"Document:\n{excerpt}"
            )
            if not llm_engine._loaded:
                llm_engine.load_model()
            if llm_engine._model is not None:
                analysis = llm_engine.generate(prompt, max_tokens=400)
            elif gemini_client.is_configured:
                analysis = gemini_client.analyze_document(excerpt)
        except Exception as exc:
            logger.warning("Document AI analysis unavailable: %s", exc)

        if not analysis:
            analysis = (
                f"Extraction completed for '{filename}'. No local or cloud AI model is available "
                f"for interpretation. Review the extracted text with a qualified clinician. "
                f"Characters: {len(result['raw_text'])}; chunks: {result['chunk_count']}; "
                f"RAG chunks stored: {chunks_added}."
            )

        # Persist to SQLite
        doc_id = db_manager.save_document(
            filename=filename,
            file_type=result["file_type"],
            content=result["raw_text"][:5000],   # store first 5k chars
            analysis_result=analysis,
            user_id=user_id,
            patient_id=patient_id,
            char_count=len(result["raw_text"]),
            chunk_count=result["chunk_count"],
            chunks_added_to_rag=chunks_added,
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
