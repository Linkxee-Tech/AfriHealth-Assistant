"""
Admin routes — /admin/*
  GET  /admin/stats              — global usage statistics
  GET  /admin/users              — list all users
  PATCH /admin/users/{user_id}/status — toggle active/blocked
  DELETE /admin/users/{user_id}  — permanently delete a user
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from pydantic import BaseModel

from backend.api.dependencies.auth import get_current_user
from backend.database.db_manager import get_db, db_manager
from backend.database.models import User, Conversation, Message, Patient, Document

admin_router = APIRouter(prefix="/admin", tags=["Admin"])


def _require_admin(current_user):
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this resource",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Stats
# ─────────────────────────────────────────────────────────────────────────────
@admin_router.get("/stats", summary="Get global usage statistics")
async def get_admin_stats(current_user=Depends(get_current_user), db=Depends(get_db)):
    """Returns total users, conversations, messages, patients, docs, and feedback stats."""
    _require_admin(current_user)

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
            "down": thumbs_down,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# User management
# ─────────────────────────────────────────────────────────────────────────────
@admin_router.get("/users", summary="List all users")
async def list_users(current_user=Depends(get_current_user), db=Depends(get_db)):
    """Returns all registered users with their status."""
    _require_admin(current_user)
    users = db.query(User).order_by(User.created_at).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_admin": bool(u.is_admin),
            "is_active": bool(u.is_active),
            "created_at": str(u.created_at),
        }
        for u in users
    ]


class StatusUpdate(BaseModel):
    is_active: bool


@admin_router.patch("/users/{user_id}/status", summary="Block or unblock a user account")
async def update_user_status(
    user_id: int,
    body: StatusUpdate,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Toggle the is_active flag for a user. Blocked users cannot log in."""
    _require_admin(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_admin and not body.is_active:
        raise HTTPException(
            status_code=400, detail="Cannot block an admin account"
        )
    if user.username == current_user.username:
        raise HTTPException(
            status_code=400, detail="Cannot block your own account"
        )

    user.is_active = body.is_active
    db.commit()
    action = "unblocked" if body.is_active else "blocked"
    return {"success": True, "message": f"User '{user.username}' has been {action}"}


@admin_router.delete("/users/{user_id}", summary="Permanently delete a user")
async def delete_user(
    user_id: int,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Permanently remove a user and all their data."""
    _require_admin(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="Cannot delete an admin account")
    if user.username == current_user.username:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    db.delete(user)
    db.commit()
    return {"success": True, "message": f"User '{user.username}' permanently deleted"}
