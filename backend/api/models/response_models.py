"""Pydantic response models for all API endpoints."""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
    session_id: str = ""
    elapsed_ms: float = 0.0
    language: str = "English"
    knowledge_base_hits: int = 0


class ConversationSummary(BaseModel):
    id: int
    session_id: str
    topic: str
    started_at: str
    msg_count: int


class MessageOut(BaseModel):
    role: str
    content: str
    sources: List[str] = []
    timestamp: str = ""


class HealthMetricOut(BaseModel):
    id: int
    metric_type: str
    value: str
    unit: str = ""
    notes: str = ""
    recorded_at: str


class VitalCheckResponse(BaseModel):
    metric_type: str
    value: str
    status: str
    urgency: str
    message: str


class SymptomAnalysisResponse(BaseModel):
    urgency: str
    advice: str
    do_not: List[str] = []


class ClinicalSupportResponse(BaseModel):
    urgency: str
    advice: str
    do_not: List[str] = []
    identified_risk_factors: List[str] = []
    epidemiological_flags: List[str] = []
    chw_action_plan: str = ""


class PersonalizedCoachResponse(BaseModel):
    insights: List[str] = []
    risk_alerts: List[str] = []
    recommendations: List[str] = []
    follow_up: List[str] = []


class MedicationInteractionResponse(BaseModel):
    interactions: List[str] = []
    safe_to_continue: bool = True
    notes: List[str] = []


class TreatmentProtocolResponse(BaseModel):
    condition: str
    protocol: List[str] = []
    references: List[str] = []


class DocumentAnalysisResponse(BaseModel):
    doc_id: int
    filename: str
    file_type: str
    char_count: int
    chunk_count: int
    chunks_added_to_rag: int
    extracted_text_preview: str
    analysis: str


class SystemStatusResponse(BaseModel):
    app_name: str
    version: str
    model_loaded: bool
    model_path: str
    stub_mode: bool
    memory_usage_gb: float
    load_time_ms: float
    knowledge_base_docs: int
    cpu_percent: float
    memory_used_gb: float
    memory_total_gb: float
    memory_percent: float


class SuccessResponse(BaseModel):
    success: bool
    message: str = ""


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
