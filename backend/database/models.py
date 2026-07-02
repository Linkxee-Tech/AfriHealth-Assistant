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
    metric_type = Column(String(50), nullable=False)
    value       = Column(String(100), nullable=False)
    unit        = Column(String(20))
    notes       = Column(Text)
    recorded_at = Column(DateTime, default=func.now())

    user        = relationship("User", back_populates="health_metrics")


class Document(Base):
    __tablename__ = "documents"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename        = Column(String(255), nullable=False)
    file_type       = Column(String(50))
    content         = Column(Text)
    analysis_result = Column(Text)
    uploaded_at     = Column(DateTime, default=func.now())

    user            = relationship("User", back_populates="documents")
