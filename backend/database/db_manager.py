"""
Database manager — SQLite via SQLAlchemy.
All CRUD operations for conversations, health metrics, and documents.
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session

from backend.config import settings
from backend.database.models import Base, Conversation, Message, HealthMetric, Document, User
from backend.utils.logger import get_logger
from backend.utils.helpers import now_str

logger = get_logger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.DB_PATH
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
            echo=settings.DEBUG,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def init_tables(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables initialised at %s", self.db_path)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def get_session(self) -> Session:
        return self.SessionLocal()

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    def get_user_by_username(self, username: str):
        with self.get_session() as db:
            return db.query(User).filter(User.username == username).first()

    def create_user(self, username: str, password_hash: str):
        with self.get_session() as db:
            user = User(username=username, password_hash=password_hash)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user

    # ------------------------------------------------------------------
    # Conversations
    # ------------------------------------------------------------------
    def save_conversation(self, messages: List[Dict], session_id: str = None, user_id: int = None) -> str:
        """Save a full conversation (list of {role, content, sources}) and return session_id."""
        if not messages:
            return ""
        session_id = session_id or str(uuid.uuid4())
        topic = messages[0]["content"][:80] if messages else "Untitled"

        with self.get_session() as db:
            conv = Conversation(session_id=session_id, topic=topic, user_id=user_id)
            db.add(conv)
            db.flush()
            for m in messages:
                msg = Message(
                    conversation_id=conv.id,
                    role=m["role"],
                    content=m["content"],
                    sources=json.dumps(m.get("sources", [])),
                )
                db.add(msg)
            db.commit()
            logger.info("Saved conversation %s (%d messages)", session_id, len(messages))
        return session_id

    def get_conversations(self, limit: int = 100, user_id: int = None) -> List[Dict]:
        with self.get_session() as db:
            q = db.query(Conversation)
            if user_id:
                q = q.filter(Conversation.user_id == user_id)
            convs = q.order_by(desc(Conversation.started_at)).limit(limit).all()
            result = []
            for c in convs:
                result.append({
                    "id": c.id,
                    "session_id": c.session_id,
                    "topic": c.topic,
                    "started_at": c.started_at.strftime("%Y-%m-%d %H:%M") if c.started_at else "",
                    "msg_count": len(c.messages),
                })
        return result

    def get_conversation_messages(self, session_id: str) -> List[Dict]:
        with self.get_session() as db:
            conv = db.query(Conversation).filter(
                Conversation.session_id == session_id
            ).first()
            if not conv:
                return []
            return [
                {
                    "role": m.role,
                    "content": m.content,
                    "sources": json.loads(m.sources or "[]"),
                    "timestamp": m.timestamp.strftime("%H:%M") if m.timestamp else "",
                }
                for m in conv.messages
            ]

    def delete_conversation(self, session_id: str) -> bool:
        with self.get_session() as db:
            conv = db.query(Conversation).filter(
                Conversation.session_id == session_id
            ).first()
            if not conv:
                return False
            db.delete(conv)
            db.commit()
            logger.info("Deleted conversation %s", session_id)
        return True

    # ------------------------------------------------------------------
    # Health metrics
    # ------------------------------------------------------------------
    def save_health_metric(
        self,
        metric_type: str,
        value: str,
        unit: str = "",
        notes: str = "",
        user_id: int = None,
    ) -> int:
        with self.get_session() as db:
            entry = HealthMetric(
                metric_type=metric_type,
                value=value,
                unit=unit,
                notes=notes or None,
                user_id=user_id,
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            logger.info("Saved health metric: %s = %s %s", metric_type, value, unit)
            return entry.id

    def get_health_metrics(
        self,
        metric_type: str = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 200,
        user_id: int = None,
    ) -> List[Dict]:
        with self.get_session() as db:
            q = db.query(HealthMetric)
            if user_id:
                q = q.filter(HealthMetric.user_id == user_id)
            if metric_type:
                q = q.filter(HealthMetric.metric_type == metric_type)
            if start_date:
                q = q.filter(HealthMetric.recorded_at >= start_date)
            if end_date:
                q = q.filter(HealthMetric.recorded_at <= end_date)
            rows = q.order_by(desc(HealthMetric.recorded_at)).limit(limit).all()
        return [
            {
                "id": r.id,
                "metric_type": r.metric_type,
                "value": r.value,
                "unit": r.unit or "",
                "notes": r.notes or "",
                "recorded_at": r.recorded_at.strftime("%Y-%m-%d %H:%M") if r.recorded_at else "",
            }
            for r in rows
        ]

    def delete_health_metric(self, entry_id: int) -> bool:
        with self.get_session() as db:
            entry = db.query(HealthMetric).filter(HealthMetric.id == entry_id).first()
            if not entry:
                return False
            db.delete(entry)
            db.commit()
        return True

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------
    def save_document(
        self,
        filename: str,
        file_type: str,
        content: str = "",
        analysis_result: str = "",
        user_id: int = None,
    ) -> int:
        with self.get_session() as db:
            doc = Document(
                filename=filename,
                file_type=file_type,
                content=content,
                analysis_result=analysis_result,
                user_id=user_id,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            return doc.id

    def get_documents(self, limit: int = 50, user_id: int = None) -> List[Dict]:
        with self.get_session() as db:
            q = db.query(Document)
            if user_id:
                q = q.filter(Document.user_id == user_id)
            docs = q.order_by(desc(Document.uploaded_at)).limit(limit).all()
        return [
            {
                "id": d.id,
                "filename": d.filename,
                "file_type": d.file_type,
                "analysis_result": d.analysis_result or "",
                "uploaded_at": d.uploaded_at.strftime("%Y-%m-%d %H:%M") if d.uploaded_at else "",
            }
            for d in docs
        ]


# Singleton instance used across the app
db_manager = DatabaseManager()
