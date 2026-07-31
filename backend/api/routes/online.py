import datetime as dt
import io
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import Dict, Any

from backend.api.dependencies.auth import get_current_user
from backend.core.hybrid_orchestrator import hybrid_orchestrator
from backend.database.db_manager import get_db
from backend.database.models import Conversation, Document, HealthMetric, Message, Patient, Settings
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

online_router = APIRouter(prefix="/online", tags=["Online Features"])

class SearchRequest(BaseModel):
    query: str
    limit: int = Field(5, ge=1, le=10)

@online_router.get("/status")
async def get_online_status():
    """Check network connectivity status and hybrid mode readiness."""
    is_online = hybrid_orchestrator.is_online()
    return {
        "status": "online" if is_online else "offline",
        "hybrid_mode_active": is_online,
        "search_engine": "DuckDuckGo" if is_online else None
    }

@online_router.post("/search")
async def perform_search(request: SearchRequest, current_user = Depends(get_current_user)):
    """Perform a direct online search (used by frontend settings/testing)."""
    if not hybrid_orchestrator.is_online():
        return {"results": [], "error": "Offline mode active"}
    
    results = hybrid_orchestrator.search_online(request.query, limit=request.limit)
    return {"results": results}

@online_router.post("/sync")
async def sync_data(current_user = Depends(get_current_user)):
    """Report that cloud sync is unavailable until a provider is configured."""
    raise HTTPException(
        status_code=501,
        detail="Cloud synchronization is not configured. Use Download Backup for a local export.",
    )

def _iso(value):
    return value.isoformat() if isinstance(value, (dt.datetime, dt.date)) else value


@online_router.get("/backup", summary="Download a local user backup")
async def download_backup(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Export only the authenticated user's records as a real JSON backup."""
    conversations = db.query(Conversation).filter(Conversation.user_id == current_user.id).all()
    payload = {
        "format": "afrihealth-user-backup",
        "version": 1,
        "exported_at": dt.datetime.utcnow().isoformat() + "Z",
        "user_id": current_user.id,
        "conversations": [],
        "health_metrics": [],
        "documents": [],
        "patients": [],
        "settings": [],
    }
    for conversation in conversations:
        item = {column.name: _iso(getattr(conversation, column.name)) for column in Conversation.__table__.columns}
        item["messages"] = [
            {column.name: _iso(getattr(message, column.name)) for column in Message.__table__.columns}
            for message in conversation.messages
        ]
        payload["conversations"].append(item)
    for key, model, query in (
        ("health_metrics", HealthMetric, db.query(HealthMetric).filter(HealthMetric.user_id == current_user.id)),
        ("documents", Document, db.query(Document).filter(Document.user_id == current_user.id)),
        ("patients", Patient, db.query(Patient).filter(Patient.user_id == current_user.id)),
        ("settings", Settings, db.query(Settings).filter(Settings.key.like(f"user:{current_user.id}:%"))),
    ):
        payload[key] = [
            {column.name: _iso(getattr(row, column.name)) for column in model.__table__.columns}
            for row in query.all()
        ]
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    filename = f"afrihealth-backup-user-{current_user.id}.json"
    return StreamingResponse(
        io.BytesIO(raw),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@online_router.post("/backup", summary="Download a local user backup")
async def backup_data(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """POST compatibility endpoint that returns the same real local backup."""
    return await download_backup(current_user=current_user, db=db)

@online_router.post("/update")
async def update_knowledge_base(current_user = Depends(get_current_user)):
    """Return the locally verifiable update state; no remote updater is configured."""
    return {
        "success": False,
        "available": False,
        "message": "Automatic model and knowledge-base updates are not configured.",
    }

@online_router.post("/telemedicine")
async def connect_telemedicine(current_user = Depends(get_current_user)):
    """Telemedicine requires an explicitly configured external provider."""
    raise HTTPException(status_code=501, detail="No telemedicine provider is configured.")

class GeminiRequest(BaseModel):
    prompt: str
    use_stream: bool = False

@online_router.post("/gemini")
async def test_gemini(request: GeminiRequest, current_user = Depends(get_current_user)):
    """Test the configured Gemini cloud provider connection."""
    from backend.core.gemini_integration import gemini_client
    if not gemini_client.is_configured:
        return {"success": False, "error": "Gemini API key not configured"}
    
    try:
        if request.use_stream:
            return StreamingResponse(
                gemini_client.stream_generate(request.prompt),
                media_type="text/plain",
                headers={"X-AfriHealth-Provider": gemini_client.model_name},
            )
        else:
            response_text = gemini_client.generate(request.prompt)
            return {"success": True, "response": response_text}
    except Exception as e:
        return {"success": False, "error": str(e)}


@online_router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...), current_user = Depends(get_current_user)):
    """Transcribe a captured voice question when the cloud provider is configured."""
    from backend.core.gemini_integration import gemini_client

    if not gemini_client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Voice transcription is unavailable. Configure the cloud provider or use typed input.",
        )
    contents = await audio.read()
    if not contents:
        raise HTTPException(status_code=400, detail="The audio recording is empty.")
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio recording is too large. Keep it under 10 MB.")
    try:
        text = gemini_client.transcribe_audio(contents, audio.content_type or "audio/wav")
        return {"success": True, "text": text}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Audio transcription failed: {exc}") from exc


@online_router.get("/cost")
async def gemini_cost(current_user = Depends(get_current_user)):
    from backend.core.gemini_integration import gemini_client
    return gemini_client.check_cost()
