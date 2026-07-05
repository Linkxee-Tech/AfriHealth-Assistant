"""
SQLAlchemy ORM models — matches spec data model exactly.

Tables:
  conversations  — one row per session header
  messages       — one row per turn (user or assistant)
  health_metrics — health readings
  documents      — uploaded document records
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at    = Column(DateTime, default=func.now())
    is_active     = Column(Boolean, default=True)

    conversations  = relationship("Conversation", back_populates="user")
    health_metrics = relationship("HealthMetric", back_populates="user")
    documents      = relationship("Document", back_populates="user")


class Conversation(Base):
    __tablename__ = "conversations"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(String(50), unique=True, nullable=False, index=True)
    topic      = Column(String(255), nullable=False)
    started_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    messages   = relationship("Message", back_populates="conversation",
                               cascade="all, delete-orphan")
    user       = relationship("User", back_populates="conversations")


class Message(Base):
    __tablename__ = "messages"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role            = Column(String(20), nullable=False)   # "user" | "assistant"
    content         = Column(Text, nullable=False)
    sources         = Column(Text)                          # JSON string
    timestamp       = Column(DateTime, default=func.now())

    conversation    = relationship("Conversation", back_populates="messages")


class HealthMetric(Base):
    __tablename__ = "health_metrics"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    patient_id  = Column(Integer, ForeignKey("patients.id"), nullable=True)
    metric_type = Column(String(50), nullable=False)
    value       = Column(String(100), nullable=False)
    unit        = Column(String(20))
    notes       = Column(Text)
    recorded_at = Column(DateTime, default=func.now())

    user        = relationship("User", back_populates="health_metrics")
    patient     = relationship("Patient", back_populates="health_metrics")


class Document(Base):
    __tablename__ = "documents"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=True)
    patient_id      = Column(Integer, ForeignKey("patients.id"), nullable=True)
    filename        = Column(String(255), nullable=False)
    file_type       = Column(String(50))
    content         = Column(Text)
    analysis_result = Column(Text)
    uploaded_at     = Column(DateTime, default=func.now())

    user            = relationship("User", back_populates="documents")
    patient         = relationship("Patient", back_populates="documents")


# ------------------------------------------------------------------
# Patient Management Module
# ------------------------------------------------------------------

class Patient(Base):
    __tablename__ = 'patients'
    
    id = Column(Integer, primary_key=True)
    mrn = Column(String(20), unique=True, index=True) # Medical Record Number
    first_name = Column(String(50))
    last_name = Column(String(50))
    gender = Column(String(10))
    date_of_birth = Column(DateTime)
    phone = Column(String(20))
    emergency_contact = Column(String(100))
    address = Column(String(200))
    blood_type = Column(String(5))
    allergies = Column(Text)
    medical_history = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    visits = relationship("Visit", back_populates="patient", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="patient", cascade="all, delete-orphan")
    health_metrics = relationship("HealthMetric", back_populates="patient", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="patient", cascade="all, delete-orphan")

class Visit(Base):
    __tablename__ = 'visits'
    
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey('patients.id'))
    visit_date = Column(DateTime, default=func.now())
    visit_type = Column(String(50))  # Initial / Follow-up / Emergency
    chief_complaint = Column(Text)
    history = Column(Text)
    examination = Column(Text)
    diagnosis = Column(Text)
    ai_suggestions = Column(Text)
    medications = Column(Text)  # JSON: [{name, dosage, frequency}]
    tests = Column(Text)
    referral = Column(Text)
    next_visit = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    patient = relationship("Patient", back_populates="visits")
    prescriptions = relationship("Prescription", back_populates="visit", cascade="all, delete-orphan")

class Prescription(Base):
    __tablename__ = 'prescriptions'
    
    id = Column(Integer, primary_key=True)
    visit_id = Column(Integer, ForeignKey('visits.id'))
    patient_id = Column(Integer, ForeignKey('patients.id'))
    medication = Column(String(100))
    dosage = Column(String(50))
    frequency = Column(String(50))
    duration = Column(String(50))
    prescribed_at = Column(DateTime, default=func.now())
    
    patient = relationship("Patient", back_populates="prescriptions")
    visit = relationship("Visit", back_populates="prescriptions")

# ------------------------------------------------------------------
# Clinical & Settings Models
# ------------------------------------------------------------------

class ClinicalGuideline(Base):
    __tablename__ = 'clinical_guidelines'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100))
    content = Column(Text, nullable=False)
    source = Column(String(255))
    created_at = Column(DateTime, default=func.now())

class Drug(Base):
    __tablename__ = 'drugs'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    category = Column(String(100))
    dosage_info = Column(Text)
    side_effects = Column(Text)
    contraindications = Column(Text)
    interactions = Column(Text)  # JSON string

class Settings(Base):
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False, index=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
