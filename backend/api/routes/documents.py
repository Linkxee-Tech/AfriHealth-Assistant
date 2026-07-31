"""
Document routes — /documents/upload, /documents/analyze
Blueprint: documents_router
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends, Query
from typing import List, Dict, Optional

from backend.api.models.response_models import DocumentAnalysisResponse, SuccessResponse
from backend.services.document_service import document_service
from backend.database.db_manager import db_manager
from backend.api.dependencies.auth import get_current_user
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
    response_model=Dict,
    summary="Upload and analyze a medical document",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    patient_id: Optional[int] = Form(None),
    current_user = Depends(get_current_user)
):
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

    suffix = (file.filename or "").lower().rsplit(".", 1)[-1]
    allowed_suffixes = {"pdf", "docx", "txt", "md", "jpg", "jpeg", "png", "bmp"}
    if file.content_type not in ALLOWED_TYPES and suffix not in allowed_suffixes:
        raise HTTPException(
            status_code=415,
            detail="Unsupported document type. Use PDF, DOCX, TXT, JPG, PNG, or BMP.",
        )

    if patient_id is not None and not db_manager.get_patient(patient_id, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="Patient not found")

    try:
        background_tasks.add_task(
            document_service.process_and_store,
            file_bytes=contents,
            filename=file.filename or "unnamed",
            user_id=current_user.id,
            patient_id=patient_id
        )
        return {"status": "processing", "filename": file.filename, "message": "Document uploaded and processing in background."}
    except Exception as exc:
        logger.error("Document processing error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@documents_router.post(
    "/analyze",
    response_model=DocumentAnalysisResponse,
    summary="Analyze an already-uploaded document by filename",
)
async def analyze_document(payload: dict, current_user = Depends(get_current_user)):
    """Re-analyze a document by filename from the database."""
    filename = payload.get("filename", "")
    if not filename:
        raise HTTPException(status_code=422, detail="filename is required.")
    docs = db_manager.get_documents(limit=500, user_id=current_user.id)
    doc_summary = next((d for d in docs if d["filename"] == filename), None)
    doc = db_manager.get_document(doc_summary["id"], user_id=current_user.id) if doc_summary else None
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found.")
    return DocumentAnalysisResponse(
        doc_id=doc["id"],
        filename=doc["filename"],
        file_type=doc.get("file_type", ""),
        char_count=doc["char_count"],
        chunk_count=doc["chunk_count"],
        chunks_added_to_rag=doc["chunks_added_to_rag"],
        extracted_text_preview=doc["content"][:500],
        analysis=doc.get("analysis_result", ""),
    )


@documents_router.get(
    "",
    summary="Get user's or patient's uploaded documents",
)
async def get_documents(
    patient_id: Optional[int] = Query(None, description="Filter by Patient ID"),
    limit: int = Query(50, ge=1, le=500),
    current_user = Depends(get_current_user)
):
    return db_manager.get_documents(user_id=current_user.id, patient_id=patient_id, limit=limit)
