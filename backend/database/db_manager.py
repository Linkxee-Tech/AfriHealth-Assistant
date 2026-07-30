"""
Database manager — SQLite via SQLAlchemy.
All CRUD operations for conversations, health metrics, and documents.
"""

import json
import uuid
import datetime
import hashlib
import secrets
from typing import List, Optional, Dict, Any

from sqlalchemy import create_engine, desc, inspect, text, func
from sqlalchemy.orm import sessionmaker, Session

from backend.config import settings, resolve_project_path
from backend.database.models import (
    Base, Conversation, Message, HealthMetric, Document, User,
    Patient, Visit, Prescription, ClinicalGuideline, Drug, PasswordReset
)
from backend.utils.logger import get_logger
from backend.utils.helpers import now_str

logger = get_logger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str = None):
        # Resolve relative paths from the repository root so starting Uvicorn
        # from the root or backend directory always uses the same database.
        self.db_path = str(resolve_project_path(db_path or settings.DB_PATH))
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
            echo=settings.DEBUG,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine, expire_on_commit=False
        )
        Base.metadata.create_all(bind=self.engine)
        self._run_migrations()

    def _run_migrations(self):
        """Add compatibility columns to databases created before patient support."""
        inspector = inspect(self.engine)
        migrations = {
            "patients": (
                "user_id",
                "ALTER TABLE patients ADD COLUMN user_id INTEGER REFERENCES users(id)",
            ),
            "health_metrics": (
                "patient_id",
                "ALTER TABLE health_metrics ADD COLUMN patient_id INTEGER REFERENCES patients(id)",
            ),
            "documents": (
                "patient_id",
                "ALTER TABLE documents ADD COLUMN patient_id INTEGER REFERENCES patients(id)",
            ),
            "documents_char_count": (
                "char_count",
                "ALTER TABLE documents ADD COLUMN char_count INTEGER DEFAULT 0",
            ),
            "documents_chunk_count": (
                "chunk_count",
                "ALTER TABLE documents ADD COLUMN chunk_count INTEGER DEFAULT 0",
            ),
            "documents_chunks_added": (
                "chunks_added_to_rag",
                "ALTER TABLE documents ADD COLUMN chunks_added_to_rag INTEGER DEFAULT 0",
            ),
            "users_email": (
                "email",
                "ALTER TABLE users ADD COLUMN email VARCHAR(255)",
            ),
            "users_is_admin": (
                "is_admin",
                "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0",
            ),
            "messages_feedback": (
                "feedback",
                "ALTER TABLE messages ADD COLUMN feedback INTEGER DEFAULT 0",
            ),
        }

        with self.engine.begin() as conn:
            for table_key, (column, statement) in migrations.items():
                if table_key.startswith("documents_"):
                    table = "documents"
                elif table_key.startswith("users_"):
                    table = "users"
                elif table_key == "messages_feedback":
                    table = "messages"
                else:
                    table = table_key
                existing_columns = {
                    item["name"] for item in inspector.get_columns(table)
                }
                if column not in existing_columns:
                    conn.execute(text(statement))
                    logger.info("Added %s.%s compatibility column", table, column)

    def init_tables(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(bind=self.engine)
        self._seed_reference_data()
        self.init_medications_table()
        # Seed default admin user if not exists
        with self.get_session() as db:
            admin_user = db.query(User).filter(User.username == "admin").first()
            if not admin_user:
                try:
                    import bcrypt
                    hashed = bcrypt.hashpw("adminpassword".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    # Set is_admin=True
                    user = User(username="admin", password_hash=hashed, is_admin=True)
                    db.add(user)
                    db.commit()
                    logger.info("Default admin user created (username: admin, password: adminpassword)")
                except Exception as exc:
                    logger.error("Failed to seed admin user: %s", exc)
        logger.info("Database tables initialised at %s", self.db_path)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def close_session(self, session: Session) -> None:
        session.close()

    def _seed_reference_data(self) -> None:
        """Install source-labelled reference data once for the clinical UI."""
        with self.get_session() as db:
            if db.query(ClinicalGuideline).count() == 0:
                db.add_all([
                    ClinicalGuideline(title="WHO malaria guidance", category="Infectious Diseases", content="Use current WHO malaria guidance and local test-and-treat protocols. Confirm diagnosis, severity, pregnancy status, age, weight, and medicine availability before treatment.", source="WHO malaria source documents in backend/data/raw_data/who_guidelines"),
                    ClinicalGuideline(title="WHO sanitation and health", category="Public Health", content="Safe water, sanitation, hygiene, and community prevention reduce enteric and waterborne disease risk. Escalate suspected severe dehydration or sepsis urgently.", source="WHO Guidelines on sanitation and health"),
                    ClinicalGuideline(title="WHO digital health strategy", category="Health Systems", content="Digital tools support—not replace—qualified clinical judgement, privacy controls, and local health-system workflows.", source="Global strategy on digital health"),
                ])
            if db.query(Drug).count() == 0:
                db.add_all([
                    Drug(name="paracetamol", category="Analgesic/antipyretic", dosage_info="Use only an approved product label or clinician-verified dose; check age, weight, liver disease, and duplicate products.", side_effects="Usually well tolerated at labelled doses; overdose can cause severe liver injury.", contraindications="Severe liver disease or known allergy; seek professional advice.", interactions='[{"with":"other paracetamol products","severity":"high","note":"avoid duplicate dosing"}]'),
                    Drug(name="artemether-lumefantrine", category="Antimalarial", dosage_info="Follow the current WHO/local malaria protocol and exact product label by weight/age.", side_effects="Nausea, headache, dizziness; seek care for severe or unusual symptoms.", contraindications="Requires clinician review for pregnancy, severe malaria, QT-risk medicines, and inability to take oral treatment.", interactions='[]'),
                    Drug(name="amoxicillin", category="Antibiotic", dosage_info="Prescription medicine. Dose and duration depend on indication, age/weight, renal function, and local protocol.", side_effects="Nausea, diarrhoea, rash; urgent care for breathing difficulty or facial swelling.", contraindications="Penicillin allergy and selected infectious syndromes; clinician review required.", interactions='[]'),
                ])
            db.commit()

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    def get_user_by_username(self, username: str):
        with self.get_session() as db:
            normalized = (username or "").strip().lower()
            return db.query(User).filter(func.lower(User.username) == normalized).first()

    def get_user_by_email(self, email: str):
        with self.get_session() as db:
            normalized = (email or "").strip().lower()
            return db.query(User).filter(func.lower(User.email) == normalized).first()

    def create_user(self, username: str, password_hash: str, email: str = None, is_admin: bool = False):
        with self.get_session() as db:
            user = User(username=username, password_hash=password_hash, email=email or None, is_admin=is_admin)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user

    def create_password_reset(self, username: str = None, email: str = None, ttl_minutes: int = 30):
        """Create a hashed, expiring one-time token without exposing user data."""
        with self.get_session() as db:
            query = db.query(User)
            if username:
                user = query.filter(func.lower(User.username) == username.strip().lower()).first()
            else:
                user = query.filter(func.lower(User.email) == email.strip().lower()).first()
            if not user:
                return None
            # Local recovery uses a compact 8-character URL-safe code. It is
            # still stored only as a SHA-256 hash and remains single-use and
            # time-limited.
            raw_token = secrets.token_urlsafe(6)
            token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
            now = datetime.datetime.utcnow()
            db.query(PasswordReset).filter(PasswordReset.user_id == user.id, PasswordReset.used_at.is_(None)).update({"used_at": now})
            db.add(PasswordReset(user_id=user.id, token_hash=token_hash, expires_at=now + datetime.timedelta(minutes=ttl_minutes)))
            db.commit()
            return {"username": user.username, "email": user.email, "token": raw_token}

    def consume_password_reset(self, raw_token: str, password_hash: str) -> bool:
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        with self.get_session() as db:
            reset = db.query(PasswordReset).filter(PasswordReset.token_hash == token_hash, PasswordReset.used_at.is_(None)).first()
            if not reset or reset.expires_at < datetime.datetime.utcnow():
                return False
            user = db.query(User).filter(User.id == reset.user_id).first()
            if not user:
                return False
            user.password_hash = password_hash
            reset.used_at = datetime.datetime.utcnow()
            db.commit()
            return True

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
            if conv and user_id is not None and conv.user_id not in (None, user_id):
                raise PermissionError("Conversation belongs to another user")
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
                    feedback=m.get("feedback", 0),
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

    def get_conversation_messages(self, session_id: str, user_id: int = None) -> List[Dict]:
        with self.get_session() as db:
            query = db.query(Conversation).filter(Conversation.session_id == session_id)
            if user_id is not None:
                query = query.filter(Conversation.user_id == user_id)
            conv = query.first()
            if not conv:
                return []
            return [
                {
                    "role": m.role,
                    "content": m.content,
                    "sources": json.loads(m.sources or "[]"),
                    "timestamp": m.timestamp.strftime("%H:%M") if m.timestamp else "",
                    "feedback": getattr(m, "feedback", 0),
                }
                for m in conv.messages
            ]

    def delete_conversation(self, session_id: str, user_id: int = None) -> bool:
        with self.get_session() as db:
            query = db.query(Conversation).filter(Conversation.session_id == session_id)
            if user_id is not None:
                query = query.filter(Conversation.user_id == user_id)
            conv = query.first()
            if not conv:
                return False
            db.delete(conv)
            db.commit()
            logger.info("Deleted conversation %s", session_id)
        return True

    def delete_all_conversations(self, user_id: int) -> int:
        """Delete every conversation owned by a user and return the count."""
        with self.get_session() as db:
            conversations = db.query(Conversation).filter(Conversation.user_id == user_id).all()
            count = len(conversations)
            for conversation in conversations:
                db.delete(conversation)
            db.commit()
        return count

    # ------------------------------------------------------------------
    # Health metrics
    # ------------------------------------------------------------------
    def add_health_entry(self, user_id: int, metric_type: str, value: str, unit: str, notes: str = None, patient_id: int = None, recorded_at=None) -> int:
        with self.get_session() as db:
            if patient_id is not None:
                patient = db.query(Patient).filter(Patient.id == patient_id).first()
                if not patient or (user_id is not None and patient.user_id not in (None, user_id)):
                    raise ValueError("Patient not found or does not belong to the current user")
            metric = HealthMetric(
                user_id=user_id,
                patient_id=patient_id,
                metric_type=metric_type,
                value=value,
                unit=unit,
                notes=notes,
                recorded_at=recorded_at,
            )
            db.add(metric)
            db.commit()
            db.refresh(metric)
            return metric.id

    def get_health_entries(
        self,
        limit: int = 200,
        user_id: int = None,
        patient_id: int = None,
        metric_type: str = None,
    ) -> List[Dict]:
        with self.get_session() as db:
            q = db.query(HealthMetric)
            if user_id is not None:
                q = q.filter(HealthMetric.user_id == user_id)
            if patient_id is not None:
                q = q.filter(HealthMetric.patient_id == patient_id)
            if metric_type:
                q = q.filter(HealthMetric.metric_type == metric_type)
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

    def delete_health_metric(self, entry_id: int, user_id: int = None) -> bool:
        with self.get_session() as db:
            query = db.query(HealthMetric).filter(HealthMetric.id == entry_id)
            if user_id is not None:
                query = query.filter(HealthMetric.user_id == user_id)
            entry = query.first()
            if not entry:
                return False
            db.delete(entry)
            db.commit()
        return True

    def delete_all_health_metrics(self, user_id: int) -> int:
        with self.get_session() as db:
            count = db.query(HealthMetric).filter(HealthMetric.user_id == user_id).delete(synchronize_session=False)
            db.commit()
        return count

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
        patient_id: int = None,
        char_count: int = 0,
        chunk_count: int = 0,
        chunks_added_to_rag: int = 0,
    ) -> int:
        with self.get_session() as db:
            if patient_id is not None:
                patient = db.query(Patient).filter(Patient.id == patient_id).first()
                if not patient or (user_id is not None and patient.user_id not in (None, user_id)):
                    raise ValueError("Patient not found or does not belong to the current user")
            doc = Document(
                filename=filename,
                file_type=file_type,
                content=content,
                analysis_result=analysis_result,
                user_id=user_id,
                patient_id=patient_id,
                char_count=char_count,
                chunk_count=chunk_count,
                chunks_added_to_rag=chunks_added_to_rag,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            return doc.id

    def get_documents(self, limit: int = 50, user_id: int = None, patient_id: int = None):
        """Fetch all documents for a user or patient."""
        with Session(self.engine) as session:
            q = session.query(Document)
            if user_id is not None:
                q = q.filter(Document.user_id == user_id)
            if patient_id:
                q = q.filter(Document.patient_id == patient_id)
            docs = q.order_by(Document.uploaded_at.desc()).limit(limit).all()
            return [
                {
                    "id": d.id,
                    "filename": d.filename,
                    "file_type": d.file_type,
                    "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
                    "analysis_result": d.analysis_result,
                    "char_count": d.char_count or 0,
                    "chunk_count": d.chunk_count or 0,
                    "chunks_added_to_rag": d.chunks_added_to_rag or 0,
                }
                for d in docs
            ]

    def get_document(self, document_id: int, user_id: int = None):
        with self.get_session() as db:
            query = db.query(Document).filter(Document.id == document_id)
            if user_id is not None:
                query = query.filter(Document.user_id == user_id)
            doc = query.first()
            if not doc:
                return None
            return {
                "id": doc.id,
                "filename": doc.filename,
                "file_type": doc.file_type or "",
                "content": doc.content or "",
                "analysis_result": doc.analysis_result or "",
                "char_count": doc.char_count or 0,
                "chunk_count": doc.chunk_count or 0,
                "chunks_added_to_rag": doc.chunks_added_to_rag or 0,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            }

    # ------------------------------------------------------------------
    # Patient Management Module (Phase 3)
    # ------------------------------------------------------------------
    def create_patient(self, data: dict, user_id: int = None) -> int:
        data = dict(data)
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

            if user_id is not None:
                data["user_id"] = user_id
            patient = Patient(**data)
            session.add(patient)
            session.commit()
            return patient.id

    def get_patients(self, search: str = None, limit: int = 100, user_id: int = None):
        with Session(self.engine) as session:
            q = session.query(Patient)
            if user_id is not None:
                q = q.filter(Patient.user_id == user_id)
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

    def get_patient(self, patient_id: int, user_id: int = None):
        with Session(self.engine) as session:
            query = session.query(Patient).filter(Patient.id == patient_id)
            if user_id is not None:
                query = query.filter(Patient.user_id == user_id)
            p = query.first()
            if not p:
                return None
            p_dict = {column.name: getattr(p, column.name) for column in p.__table__.columns}
            if p_dict.get('date_of_birth'): p_dict['date_of_birth'] = p_dict['date_of_birth'].isoformat()
            if p_dict.get('created_at'): p_dict['created_at'] = p_dict['created_at'].isoformat()
            return p_dict

    def update_patient(self, patient_id: int, data: dict, user_id: int = None):
        with Session(self.engine) as session:
            query = session.query(Patient).filter(Patient.id == patient_id)
            if user_id is not None:
                query = query.filter(Patient.user_id == user_id)
            p = query.first()
            if not p:
                return False
            for key, value in data.items():
                if hasattr(p, key) and key != "id":
                    setattr(p, key, value)
            session.commit()
            return True

    def delete_patient(self, patient_id: int, user_id: int = None):
        with Session(self.engine) as session:
            query = session.query(Patient).filter(Patient.id == patient_id)
            if user_id is not None:
                query = query.filter(Patient.user_id == user_id)
            p = query.first()
            if p:
                session.delete(p)
                session.commit()
                return True
            return False

    def create_visit(self, data: dict, user_id: int = None) -> int:
        data = dict(data)
        with Session(self.engine) as session:
            patient_query = session.query(Patient).filter(Patient.id == data.get("patient_id"))
            if user_id is not None:
                patient_query = patient_query.filter(Patient.user_id == user_id)
            if not patient_query.first():
                raise ValueError("Patient not found or does not belong to the current user")
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

    def get_patient_visits(self, patient_id: int, user_id: int = None):
        with Session(self.engine) as session:
            patient_query = session.query(Patient).filter(Patient.id == patient_id)
            if user_id is not None:
                patient_query = patient_query.filter(Patient.user_id == user_id)
            if not patient_query.first():
                return []
            visits = session.query(Visit).filter(Visit.patient_id == patient_id).order_by(Visit.visit_date.desc()).all()
            result = []
            for v in visits:
                v_dict = {col.name: getattr(v, col.name) for col in v.__table__.columns}
                if v_dict.get('visit_date'): v_dict['visit_date'] = v_dict['visit_date'].isoformat()
                if v_dict.get('next_visit'): v_dict['next_visit'] = v_dict['next_visit'].isoformat()
                if v_dict.get('created_at'): v_dict['created_at'] = v_dict['created_at'].isoformat()
                result.append(v_dict)
            return result

    def update_visit(self, visit_id: int, data: dict, user_id: int = None):
        """Update an existing visit and return whether it was found."""
        with Session(self.engine) as session:
            query = session.query(Visit).join(Patient, Visit.patient_id == Patient.id).filter(Visit.id == visit_id)
            if user_id is not None:
                query = query.filter(Patient.user_id == user_id)
            visit = query.first()
            if not visit:
                return False

            updates = dict(data)
            for field in ("visit_date", "next_visit"):
                value = updates.get(field)
                if value and isinstance(value, str):
                    try:
                        updates[field] = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
                    except ValueError:
                        return False

            for key, value in updates.items():
                if hasattr(visit, key) and key not in {"id", "patient_id"}:
                    setattr(visit, key, value)
            session.commit()
            return True

    def export_patient(self, patient_id: int, user_id: int = None):
        """Return a JSON-serialisable patient record with visit history."""
        with Session(self.engine) as session:
            query = session.query(Patient).filter(Patient.id == patient_id)
            if user_id is not None:
                query = query.filter(Patient.user_id == user_id)
            patient = query.first()
            if not patient:
                return None

            def serialise(instance):
                result = {column.name: getattr(instance, column.name) for column in instance.__table__.columns}
                for key, value in result.items():
                    if isinstance(value, (datetime.datetime, datetime.date)):
                        result[key] = value.isoformat()
                return result

            return {
                "patient": serialise(patient),
                "visits": [serialise(visit) for visit in sorted(patient.visits, key=lambda item: item.visit_date or datetime.datetime.min, reverse=True)],
            }
            
    def get_visit(self, visit_id: int, user_id: int = None):
        with Session(self.engine) as session:
            query = session.query(Visit).join(Patient, Visit.patient_id == Patient.id).filter(Visit.id == visit_id)
            if user_id is not None:
                query = query.filter(Patient.user_id == user_id)
            v = query.first()
            if not v:
                return None
            v_dict = {col.name: getattr(v, col.name) for col in v.__table__.columns}
            if v_dict.get('visit_date'): v_dict['visit_date'] = v_dict['visit_date'].isoformat()
            if v_dict.get('next_visit'): v_dict['next_visit'] = v_dict['next_visit'].isoformat()
            if v_dict.get('created_at'): v_dict['created_at'] = v_dict['created_at'].isoformat()
            return v_dict

    # -----------------------------------------------------------------------
    # Medications
    # -----------------------------------------------------------------------
    def init_medications_table(self):
        """Create medications table if it does not exist."""
        # Note: Added _get_connection helper to match requested code if missing
        if not hasattr(self, '_get_connection'):
            self._get_connection = lambda: self.engine.connect()
            
        with self._get_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS medications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    patient_id INTEGER,
                    name TEXT NOT NULL,
                    dosage TEXT,
                    frequency TEXT,
                    times TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """))
            conn.commit()

    def add_medication(self, user_id: int, name: str, dosage: str, frequency: str,
                       times: str = "[]", start_date: str = None, end_date: str = None,
                       notes: str = None, patient_id: int = None) -> int:
        if not hasattr(self, '_get_connection'):
            self._get_connection = lambda: self.engine.connect()
            
        with self._get_connection() as conn:
            cur = conn.execute(text(
                "INSERT INTO medications (user_id, patient_id, name, dosage, frequency, times, start_date, end_date, notes) "
                "VALUES (:user_id, :patient_id, :name, :dosage, :frequency, :times, :start_date, :end_date, :notes)"
            ), {
                "user_id": user_id, "patient_id": patient_id, "name": name, 
                "dosage": dosage, "frequency": frequency, "times": times, 
                "start_date": start_date, "end_date": end_date, "notes": notes
            })
            conn.commit()
            return cur.lastrowid

    def get_medications(self, user_id: int) -> list:
        import json
        if not hasattr(self, '_get_connection'):
            self._get_connection = lambda: self.engine.connect()
            
        with self._get_connection() as conn:
            rows = conn.execute(text(
                "SELECT id, name, dosage, frequency, times, start_date, end_date, notes, patient_id, created_at "
                "FROM medications WHERE user_id=:user_id ORDER BY created_at DESC"
            ), {"user_id": user_id}).fetchall()
        result = []
        for row in rows:
            # Need to convert row to dict manually since row mappings aren't directly dict constructable in all SQLAlchemy versions
            d = dict(row._mapping)
            try:
                d["times"] = json.loads(d["times"] or "[]")
            except Exception:
                d["times"] = []
            result.append(d)
        return result

    def delete_medication(self, med_id: int, user_id: int):
        if not hasattr(self, '_get_connection'):
            self._get_connection = lambda: self.engine.connect()
            
        with self._get_connection() as conn:
            conn.execute(text("DELETE FROM medications WHERE id=:id AND user_id=:user_id"), {"id": med_id, "user_id": user_id})
            conn.commit()


# Singleton instance used across the app
db_manager = DatabaseManager()

def get_db():
    db = db_manager.SessionLocal()
    try:
        yield db
    finally:
        db.close()
