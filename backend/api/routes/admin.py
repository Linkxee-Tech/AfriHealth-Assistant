"""
Admin routes — GET /admin/stats
Fetches global usage statistics for the admin dashboard.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func

from backend.api.dependencies.auth import get_current_user
from backend.database.db_manager import get_db
from backend.database.models import User, Conversation, Message, Patient, Document

admin_router = APIRouter(prefix="/admin", tags=["Admin"])


@admin_router.get("/stats", summary="Get global usage statistics")
async def get_admin_stats(current_user=Depends(get_current_user), db = Depends(get_db)):
    """Returns total users, conversations, messages, patients, docs, and feedback stats."""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can access this resource")
    
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_patients = db.query(func.count(Patient.id)).scalar() or 0
    total_documents = db.query(func.count(Document.id)).scalar() or 0
    total_conversations = db.query(func.count(Conversation.id)).scalar() or 0
    total_messages = db.query(func.count(Message.id)).scalar() or 0
    
    thumbs_up = db.query(func.count(Message.id)).filter(Message.feedback == 1).scalar() or 0
    thumbs_down = db.query(func.count(Message.id)).filter(Message.feedback == -1).scalar() or 0

    return {
        "users": total_users,
        "patients": total_patients,
        "documents": total_documents,
        "conversations": total_conversations,
        "messages": total_messages,
        "feedback": {
            "up": thumbs_up,
            "down": thumbs_down
        }
    }
