"""Chat history service."""

from typing import List, Dict, Optional
from backend.database.db_manager import db_manager
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class HistoryService:
    def list_sessions(self, limit: int = 100, user_id: int = None) -> List[Dict]:
        return db_manager.get_conversations(limit=limit, user_id=user_id)

    def get_session(self, session_id: str) -> List[Dict]:
        return db_manager.get_conversation_messages(session_id)

    def save_session(self, messages: List[Dict], session_id: str = None, user_id: int = None) -> str:
        return db_manager.save_conversation(messages, session_id=session_id, user_id=user_id)

    def delete_session(self, session_id: str) -> bool:
        return db_manager.delete_conversation(session_id)


history_service = HistoryService()
