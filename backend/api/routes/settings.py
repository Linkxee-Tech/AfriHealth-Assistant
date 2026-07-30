"""
Settings routes — GET/PUT /settings
Blueprint: settings_router
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from backend.api.dependencies.auth import get_current_user
from backend.database.db_manager import get_db
from backend.services.settings_service import SettingsService
from sqlalchemy.orm import Session
from backend.utils.logger import get_logger

logger = get_logger(__name__)
settings_router = APIRouter(prefix="/settings", tags=["Settings"])

@settings_router.get(
    "",
    response_model=Dict[str, Any],
    summary="Get user settings",
)
async def get_settings(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    return SettingsService.get_settings(db, current_user.id)

@settings_router.put(
    "",
    response_model=Dict[str, Any],
    summary="Update user settings",
)
async def update_settings(payload: dict, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    return SettingsService.update_settings(db, current_user.id, payload)


@settings_router.post("/reset", response_model=Dict[str, Any], summary="Reset user settings")
async def reset_settings(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    return SettingsService.reset_defaults(db, current_user.id)
