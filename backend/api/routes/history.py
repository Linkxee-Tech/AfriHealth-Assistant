"""
Chat history routes — GET/DELETE /chat/history
Blueprint: history_router
"""

from typing import List
from fastapi import APIRouter, HTTPException, Query

from backend.api.models.response_models import ConversationSummary, MessageOut, SuccessResponse
from backend.services.history_service import history_service
from backend.utils.logger import get_logger

logger = get_logger(__name__)
history_router = APIRouter(prefix="/chat/history", tags=["Chat History"])


@history_router.get(
    "",
    response_model=List[ConversationSummary],
    summary="List all saved conversations",
)
async def list_history(limit: int = Query(100, ge=1, le=500)):
    return history_service.list_sessions(limit=limit)


@history_router.get(
    "/{session_id}",
    response_model=List[MessageOut],
    summary="Get all messages in a conversation",
)
async def get_conversation(session_id: str):
    messages = history_service.get_session(session_id)
    if messages is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return [MessageOut(**m) for m in messages]


@history_router.post(
    "",
    response_model=SuccessResponse,
    summary="Save a conversation",
)
async def save_history(payload: dict):
    messages   = payload.get("messages", [])
    session_id = payload.get("session_id")
    sid = history_service.save_session(messages, session_id=session_id)
    return SuccessResponse(success=True, message=f"Saved session {sid}")


@history_router.delete(
    "/{session_id}",
    response_model=SuccessResponse,
    summary="Delete a conversation",
)
async def delete_conversation(session_id: str):
    deleted = history_service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return SuccessResponse(success=True, message=f"Deleted session {session_id}")
