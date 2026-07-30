"""Chat history service."""

from typing import List, Dict, Optional
from backend.database.db_manager import db_manager
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class HistoryService:
    def list_sessions(self, limit: int = 100, user_id: int = None) -> List[Dict]:
        return db_manager.get_conversations(limit=limit, user_id=user_id)

    def get_session(self, session_id: str, user_id: int = None) -> List[Dict]:
        return db_manager.get_conversation_messages(session_id, user_id=user_id)

    def save_session(self, messages: List[Dict], session_id: str = None, user_id: int = None) -> str:
        return db_manager.save_conversation(messages, session_id=session_id, user_id=user_id)

    def delete_session(self, session_id: str, user_id: int = None) -> bool:
        return db_manager.delete_conversation(session_id, user_id=user_id)

    def delete_all_sessions(self, user_id: int) -> int:
        return db_manager.delete_all_conversations(user_id=user_id)

    def save_conversation(self, messages, session_id=None, user_id=None):
        return self.save_session(messages, session_id, user_id)

    def get_conversations(self, limit=100, user_id=None):
        return self.list_sessions(limit, user_id)

    def get_conversation(self, session_id, user_id=None):
        return self.get_session(session_id, user_id)

    def delete_conversation(self, session_id, user_id=None):
        return self.delete_session(session_id, user_id)

    def export_history(self, user_id=None):
        return self.list_sessions(limit=1000, user_id=user_id)


history_service = HistoryService()
