"""
System routes — /health, /status
Blueprint: system_router
"""

from fastapi import APIRouter
from backend.api.models.response_models import SystemStatusResponse
from backend.core.llm_engine import llm_engine
from backend.core.rag_engine import rag_engine
from backend.config import settings

system_router = APIRouter(prefix="/system", tags=["System"])


@system_router.get("/health", summary="Basic health check")
async def health_check():
    """Returns 200 if the server is running."""
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@system_router.get(
    "/status",
    response_model=SystemStatusResponse,
    summary="Full model & system status",
)
async def system_status():
    """Returns model load status, memory, CPU, and knowledge base info."""
    status = llm_engine.get_status()
    return SystemStatusResponse(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        model_loaded=status.get("model_loaded", False),
        model_path=status.get("model_path", ""),
        stub_mode=status.get("stub_mode", True),
        memory_usage_gb=status.get("memory_usage_gb", 0.0),
        load_time_ms=status.get("load_time_ms", 0.0),
        knowledge_base_docs=rag_engine.get_collection_count(),
        cpu_percent=status.get("cpu_percent", 0.0),
        memory_used_gb=status.get("memory_used_gb", 0.0),
        memory_total_gb=status.get("memory_total_gb", 0.0),
        memory_percent=status.get("memory_percent", 0.0),
    )
