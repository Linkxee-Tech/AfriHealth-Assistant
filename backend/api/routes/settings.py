"""
Settings routes — GET/PUT /settings
Blueprint: settings_router
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from backend.api.dependencies.auth import get_current_user
from backend.utils.logger import get_logger

logger = get_logger(__name__)
settings_router = APIRouter(prefix="/settings", tags=["Settings"])

# Mock settings storage for now. In a real app, this goes to the DB.
USER_SETTINGS: Dict[int, Dict[str, Any]] = {}

@settings_router.get(
    "",
    response_model=Dict[str, Any],
    summary="Get user settings",
)
async def get_settings(current_user = Depends(get_current_user)):
    return USER_SETTINGS.get(current_user.id, {})

@settings_router.put(
    "",
    response_model=Dict[str, Any],
    summary="Update user settings",
)
async def update_settings(payload: dict, current_user = Depends(get_current_user)):
    USER_SETTINGS[current_user.id] = payload
    return USER_SETTINGS[current_user.id]
