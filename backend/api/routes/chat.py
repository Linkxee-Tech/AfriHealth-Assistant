"""
Chat routes — POST /chat, POST /chat/stream
Blueprint: chat_router
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from backend.api.dependencies.auth import get_current_user

from backend.api.models.request_models import ChatRequest, SaveConversationRequest
from backend.api.models.response_models import ChatResponse, SuccessResponse
from backend.services.chat_service import chat_service
from backend.utils.validators import validate_query
from backend.utils.logger import get_logger

logger = get_logger(__name__)
chat_router = APIRouter(prefix="/chat", tags=["Chat"])


@chat_router.post(
    "",
    response_model=ChatResponse,
    summary="Send a health question and get a full response",
)
async def chat(request: ChatRequest, current_user = Depends(get_current_user)):
    """
    Blocking chat endpoint.
    Retrieves relevant context from the RAG knowledge base,
    builds a prompt, and returns the full LLM response.
    """
    query = validate_query(request.query)
    try:
        result = chat_service.generate_response(
            query=query,
            language=request.language,
            session_id=request.session_id,
            top_k=request.top_k,
            detail_level=request.detail_level,
            user_id=current_user.id,
        )
        return ChatResponse(**result)
    except Exception as exc:
        logger.error("Chat error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@chat_router.post(
    "/stream",
    summary="Stream a health question response token by token",
)
async def chat_stream(request: ChatRequest, current_user = Depends(get_current_user)):
    """
    Streaming chat endpoint — returns text/event-stream.
    First chunk is a JSON sources header: __SOURCES__:[...]
    Subsequent chunks are plain text tokens.
    The Streamlit frontend consumes this via requests.get(..., stream=True).
    """
    query = validate_query(request.query)

    def token_generator():
        try:
            for token in chat_service.stream_response(
                query=query,
                language=request.language,
                session_id=request.session_id,
                top_k=request.top_k,
                detail_level=request.detail_level,
                user_id=current_user.id,
            ):
                yield token
        except Exception as exc:
            logger.error("Stream error: %s", exc)
            yield f"[Error: {exc}]"

    return StreamingResponse(token_generator(), media_type="text/plain")


@chat_router.post(
    "/save",
    response_model=SuccessResponse,
    summary="Save a conversation to history",
)
async def save_conversation(request: SaveConversationRequest, current_user = Depends(get_current_user)):
    """Persist a conversation (list of messages) to SQLite."""
    try:
        session_id = chat_service.save_conversation(
            messages=request.messages,
            session_id=request.session_id,
            user_id=current_user.id
        )
        return SuccessResponse(success=True, message=f"Saved as session {session_id}")
    except Exception as exc:
        logger.error("Save conversation error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
