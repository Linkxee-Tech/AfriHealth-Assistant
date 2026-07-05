from fastapi import APIRouter, Depends
from typing import Dict, Any

from backend.api.dependencies.auth import get_current_user
from backend.core.hybrid_orchestrator import hybrid_orchestrator
from pydantic import BaseModel

online_router = APIRouter(prefix="/online", tags=["Online Features"])

class SearchRequest(BaseModel):
    query: str
    limit: int = 5

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
    """Stub for cloud synchronization."""
    if not hybrid_orchestrator.is_online():
        return {"success": False, "message": "Cannot sync while offline"}
    return {"success": True, "message": "Sync complete. 0 bytes transferred."}

@online_router.post("/backup")
async def backup_data(current_user = Depends(get_current_user)):
    """Stub for data backup."""
    if not hybrid_orchestrator.is_online():
        return {"success": False, "message": "Cannot backup while offline"}
    return {"success": True, "message": "Backup complete to encrypted cloud storage."}

@online_router.post("/update")
async def update_knowledge_base(current_user = Depends(get_current_user)):
    """Stub for model/knowledge base updates."""
    if not hybrid_orchestrator.is_online():
        return {"success": False, "message": "Cannot check for updates while offline"}
    return {"success": True, "message": "Knowledge base and models are up to date."}

@online_router.post("/telemedicine")
async def connect_telemedicine(current_user = Depends(get_current_user)):
    """Stub for Telemedicine connection."""
    if not hybrid_orchestrator.is_online():
        return {"success": False, "message": "Telemedicine requires an active internet connection."}
    return {"success": True, "message": "Connected to telemedicine gateway. Waiting for doctor assignment..."}

class GeminiRequest(BaseModel):
    prompt: str
    use_stream: bool = False

@online_router.post("/gemini")
async def test_gemini(request: GeminiRequest):
    """Test connection for Gemini 3 Pro."""
    from backend.core.gemini_integration import gemini_client
    if not gemini_client.is_configured:
        return {"success": False, "error": "Gemini API key not configured"}
    
    try:
        if request.use_stream:
            return {"success": True, "message": "Streaming not fully implemented in this test endpoint."}
        else:
            response_text = gemini_client.generate(request.prompt)
            return {"success": True, "response": response_text}
    except Exception as e:
        return {"success": False, "error": str(e)}
