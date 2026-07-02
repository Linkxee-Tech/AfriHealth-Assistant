"""
Document routes — /documents/upload, /documents/analyze
Blueprint: documents_router
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List

from backend.api.models.response_models import DocumentAnalysisResponse, SuccessResponse
from backend.services.document_service import document_service
from backend.database.db_manager import db_manager
from backend.utils.logger import get_logger

logger = get_logger(__name__)
documents_router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "image/jpeg",
    "image/png",
    "image/bmp",
}
MAX_FILE_SIZE_MB = 20


@documents_router.post(
    "/upload",
    response_model=DocumentAnalysisResponse,
    summary="Upload and analyze a document (PDF, DOCX, TXT, image)",
)
async def upload_document(file: UploadFile = File(...)):
    """
    Accepts PDF, DOCX, TXT, JPG, PNG.
    Extracts text (OCR for images), chunks it into the RAG knowledge base,
    and returns extracted text preview + AI analysis.
    """
    # Size check
    contents = await file.read()
    size_mb  = len(contents) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum allowed: {MAX_FILE_SIZE_MB} MB.",
        )

    logger.info("Received file: %s (%s, %.2f MB)", file.filename, file.content_type, size_mb)

    try:
        result = document_service.process_and_store(
            file_bytes=contents,
            filename=file.filename or "unnamed",
        )
        return DocumentAnalysisResponse(**result)
    except Exception as exc:
        logger.error("Document processing error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@documents_router.post(
    "/analyze",
    response_model=DocumentAnalysisResponse,
    summary="Analyze an already-uploaded document by filename",
)
async def analyze_document(payload: dict):
    """Re-analyze a document by filename from the database."""
    filename = payload.get("filename", "")
    if not filename:
        raise HTTPException(status_code=422, detail="filename is required.")
    docs = db_manager.get_documents(limit=500)
    doc  = next((d for d in docs if d["filename"] == filename), None)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found.")
    return DocumentAnalysisResponse(
        doc_id=doc["id"],
        filename=doc["filename"],
        file_type=doc.get("file_type", ""),
        char_count=0,
        chunk_count=0,
        chunks_added_to_rag=0,
        extracted_text_preview="",
        analysis=doc.get("analysis_result", ""),
    )


@documents_router.get(
    "",
    summary="List all uploaded documents",
)
async def list_documents(limit: int = 50):
    return db_manager.get_documents(limit=limit)
