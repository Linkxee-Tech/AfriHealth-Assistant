"""
Database manager — SQLite via SQLAlchemy.
All CRUD operations for conversations, health metrics, and documents.
"""

import json
import uuid
import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session

from backend.config import settings
from backend.database.models import (
    Base, Conversation, Message, HealthMetric, Document, User,
    Patient, Visit, Prescription
)
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
        Base.metadata.create_all(bind=self.engine)
        self._run_migrations()

    def _run_migrations(self):
        """Safely add patient_id columns to existing tables if they don't exist."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("ALTER TABLE health_metrics ADD COLUMN patient_id INTEGER REFERENCES patients(id)"))
                conn.commit()
        except Exception:
            pass # Column likely already exists
            
        try:
            with self.engine.connect() as conn:
                conn.execute(text("ALTER TABLE documents ADD COLUMN patient_id INTEGER REFERENCES patients(id)"))
                conn.commit()
        except Exception:
            pass # Column likely already exists

    def init_tables(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables initialised at %s", self.db_path)

    def get_session(self) -> Session:
        return self.SessionLocal()

def get_db():
    db = db_manager.SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
            conv = db.query(Conversation).filter(Conversation.session_id == session_id).first()
            if not conv:
                conv = Conversation(session_id=session_id, topic=topic, user_id=user_id)
                db.add(conv)
                db.flush()
            else:
                conv.topic = topic
                db.query(Message).filter(Message.conversation_id == conv.id).delete()
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
    def add_health_entry(self, user_id: int, metric_type: str, value: str, unit: str, notes: str = None, patient_id: int = None) -> int:
        with self.get_session() as db:
            metric = HealthMetric(
                user_id=user_id,
                patient_id=patient_id,
                metric_type=metric_type,
                value=value,
                unit=unit,
                notes=notes,
            )
            db.add(metric)
            db.commit()
            db.refresh(metric)
            return metric.id

    def get_health_entries(self, limit: int = 200, user_id: int = None, patient_id: int = None) -> List[Dict]:
        with self.get_session() as db:
            q = db.query(HealthMetric)
            if patient_id:
                q = q.filter(HealthMetric.patient_id == patient_id)
            elif user_id:
                q = q.filter(HealthMetric.user_id == user_id)
            entries = q.order_by(desc(HealthMetric.recorded_at)).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "metric_type": r.metric_type,
                    "value": r.value,
                    "unit": r.unit or "",
                    "notes": r.notes or "",
                    "recorded_at": r.recorded_at.strftime("%Y-%m-%d %H:%M") if r.recorded_at else "",
                }
                for r in entries
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
        patient_id: int = None
    ) -> int:
        with self.get_session() as db:
            doc = Document(
                filename=filename,
                file_type=file_type,
                content=content,
                analysis_result=analysis_result,
                user_id=user_id,
                patient_id=patient_id
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            return doc.id

    def get_documents(self, limit: int = 50, user_id: int = None, patient_id: int = None):
        """Fetch all documents for a user or patient."""
        with Session(self.engine) as session:
            q = session.query(Document)
            if patient_id:
                q = q.filter(Document.patient_id == patient_id)
            elif user_id:
                q = q.filter(Document.user_id == user_id)
            docs = q.order_by(Document.uploaded_at.desc()).limit(limit).all()
            return [
                {
                    "id": d.id,
                    "filename": d.filename,
                    "file_type": d.file_type,
                    "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
                    "analysis_result": d.analysis_result,
                }
                for d in docs
            ]

    # ------------------------------------------------------------------
    # Patient Management Module (Phase 3)
    # ------------------------------------------------------------------
    def create_patient(self, data: dict) -> int:
        with Session(self.engine) as session:
            # Generate MRN if not provided
            if not data.get("mrn"):
                year = datetime.datetime.now().year
                count = session.query(Patient).count() + 1
                data["mrn"] = f"AH-{year}-{count:05d}"
                
            # Handle date parsing
            dob = data.get("date_of_birth")
            if dob and isinstance(dob, str):
                try:
                    data["date_of_birth"] = datetime.datetime.fromisoformat(dob.replace("Z", "+00:00"))
                except ValueError:
                    data["date_of_birth"] = None

            patient = Patient(**data)
            session.add(patient)
            session.commit()
            return patient.id

    def get_patients(self, search: str = None, limit: int = 100):
        with Session(self.engine) as session:
            q = session.query(Patient)
            if search:
                term = f"%{search}%"
                q = q.filter(
                    (Patient.first_name.ilike(term)) | 
                    (Patient.last_name.ilike(term)) | 
                    (Patient.mrn.ilike(term)) |
                    (Patient.phone.ilike(term))
                )
            patients = q.order_by(Patient.created_at.desc()).limit(limit).all()
            result = []
            for p in patients:
                p_dict = {column.name: getattr(p, column.name) for column in p.__table__.columns}
                # Convert datetime to ISO string
                if p_dict.get('date_of_birth'): p_dict['date_of_birth'] = p_dict['date_of_birth'].isoformat()
                if p_dict.get('created_at'): p_dict['created_at'] = p_dict['created_at'].isoformat()
                if p_dict.get('updated_at'): p_dict['updated_at'] = p_dict['updated_at'].isoformat()
                result.append(p_dict)
            return result

    def get_patient(self, patient_id: int):
        with Session(self.engine) as session:
            p = session.query(Patient).filter(Patient.id == patient_id).first()
            if not p:
                return None
            p_dict = {column.name: getattr(p, column.name) for column in p.__table__.columns}
            if p_dict.get('date_of_birth'): p_dict['date_of_birth'] = p_dict['date_of_birth'].isoformat()
            if p_dict.get('created_at'): p_dict['created_at'] = p_dict['created_at'].isoformat()
            return p_dict

    def update_patient(self, patient_id: int, data: dict):
        with Session(self.engine) as session:
            p = session.query(Patient).filter(Patient.id == patient_id).first()
            if not p:
                return False
            for key, value in data.items():
                if hasattr(p, key) and key != "id":
                    setattr(p, key, value)
            session.commit()
            return True

    def delete_patient(self, patient_id: int):
        with Session(self.engine) as session:
            p = session.query(Patient).filter(Patient.id == patient_id).first()
            if p:
                session.delete(p)
                session.commit()
                return True
            return False

    def create_visit(self, data: dict) -> int:
        with Session(self.engine) as session:
            visit_date = data.get("visit_date")
            if visit_date and isinstance(visit_date, str):
                try:
                    data["visit_date"] = datetime.datetime.fromisoformat(visit_date.replace("Z", "+00:00"))
                except ValueError:
                    data["visit_date"] = datetime.datetime.now()
            
            next_visit = data.get("next_visit")
            if next_visit and isinstance(next_visit, str):
                try:
                    data["next_visit"] = datetime.datetime.fromisoformat(next_visit.replace("Z", "+00:00"))
                except ValueError:
                    data["next_visit"] = None

            visit = Visit(**data)
            session.add(visit)
            session.commit()
            return visit.id

    def get_patient_visits(self, patient_id: int):
        with Session(self.engine) as session:
            visits = session.query(Visit).filter(Visit.patient_id == patient_id).order_by(Visit.visit_date.desc()).all()
            result = []
            for v in visits:
                v_dict = {c.name: getattr(v, c.name) for c.name in v.__table__.columns.keys()}
                if v_dict.get('visit_date'): v_dict['visit_date'] = v_dict['visit_date'].isoformat()
                if v_dict.get('next_visit'): v_dict['next_visit'] = v_dict['next_visit'].isoformat()
                if v_dict.get('created_at'): v_dict['created_at'] = v_dict['created_at'].isoformat()
                result.append(v_dict)
            return result
            
    def get_visit(self, visit_id: int):
        with Session(self.engine) as session:
            v = session.query(Visit).filter(Visit.id == visit_id).first()
            if not v:
                return None
            v_dict = {c.name: getattr(v, c.name) for c.name in v.__table__.columns.keys()}
            if v_dict.get('visit_date'): v_dict['visit_date'] = v_dict['visit_date'].isoformat()
            if v_dict.get('next_visit'): v_dict['next_visit'] = v_dict['next_visit'].isoformat()
            if v_dict.get('created_at'): v_dict['created_at'] = v_dict['created_at'].isoformat()
            return v_dict


# Singleton instance used across the app
db_manager = DatabaseManager()
