"""Pydantic request models for all API endpoints."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4096, description="User's health question")
    language: str = Field("English", description="Response language: English | Hausa | Swahili | Yoruba | Igbo | French | Pidgin")
    session_id: Optional[str] = Field(None, description="Optional session ID for conversation continuity")
    top_k: int = Field(3, ge=1, le=10, description="Number of RAG context chunks to retrieve")
    detail_level: str = Field("Standard", description="Response length: Brief, Standard, or Detailed")
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(None, ge=50, le=2048)

    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        allowed = {"English", "Hausa", "Swahili", "Yoruba", "Igbo", "French", "Pidgin"}
        if v not in allowed:
            raise ValueError(f"language must be one of {allowed}")
        return v
        
    @field_validator("detail_level")
    @classmethod
    def validate_detail_level(cls, v):
        allowed = {"Brief", "Standard", "Detailed"}
        if v not in allowed:
            raise ValueError(f"detail_level must be one of {allowed}")
        return v


class SaveConversationRequest(BaseModel):
    messages: List[dict] = Field(..., description="List of {role, content, sources} dicts")
    session_id: Optional[str] = None


class HealthMetricRequest(BaseModel):
    metric_type: str = Field(..., description="e.g. Blood Pressure, Heart Rate")
    value: str = Field(..., min_length=1, description="Metric value e.g. '120/80' or '72'")
    unit: str = Field("", description="Unit e.g. mmHg, bpm, kg")
    notes: Optional[str] = Field(None, description="Optional notes")


class AnalyzeVitalsRequest(BaseModel):
    metric_type: str
    value: str


class AnalyzeSymptomsRequest(BaseModel):
    symptoms: List[str] = Field(..., min_length=1, description="List of symptom strings")


class PatientContextRequest(BaseModel):
    age: Optional[int] = Field(None, ge=0, le=120, description="Patient age in years")
    gender: Optional[str] = Field(None, description="Patient gender")
    pregnant: Optional[bool] = Field(False, description="Pregnancy status")
    height_cm: Optional[float] = Field(None, gt=0, description="Height in centimeters")
    weight_kg: Optional[float] = Field(None, gt=0, description="Weight in kilograms")
    activity_level: Optional[str] = Field(None, description="Lifestyle activity level")


class PersonalizedCoachRequest(BaseModel):
    metrics: List[Dict[str, Any]] = Field(..., description="List of recorded metrics")
    patient_context: Optional[PatientContextRequest] = None


class MedicationInteractionRequest(BaseModel):
    medications: List[str] = Field(..., min_length=1, description="List of medications to check")


class TreatmentProtocolRequest(BaseModel):
    condition: str = Field(..., min_length=1, description="Medical condition for protocol lookup")


class ClinicalTriageRequest(BaseModel):
    symptoms: List[str] = Field(..., min_length=1, description="List of symptom strings")
    patient_context: Optional[PatientContextRequest] = None


# Stable public model names used by the API reference.  The aliases retain the
# existing payload shapes so current clients do not need to change.
class MetricRequest(HealthMetricRequest):
    pass


class DocumentUploadRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    patient_id: Optional[int] = Field(None, ge=1)


class SettingsRequest(BaseModel):
    values: Dict[str, Any] = Field(default_factory=dict)


class PatientRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    address: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    medical_history: Optional[str] = None
    notes: Optional[str] = None


class VisitRequest(BaseModel):
    patient_id: Optional[int] = Field(None, ge=1)
    visit_date: Optional[str] = None
    visit_type: Optional[str] = None
    chief_complaint: str = Field(..., min_length=1)
    history: Optional[str] = None
    examination: Optional[str] = None
    diagnosis: Optional[str] = None
    ai_suggestions: Optional[str] = None
    medications: Optional[str] = None
    tests: Optional[str] = None
    referral: Optional[str] = None
    next_visit: Optional[str] = None
    notes: Optional[str] = None


class ClinicalGuidelineRequest(BaseModel):
    category: Optional[str] = None
    query: Optional[str] = None


class ClinicalCDSRequest(BaseModel):
    symptoms: List[str] = Field(..., min_length=1)
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[str] = None
    pregnant: Optional[bool] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    patient_context: Optional[Dict[str, Any]] = None


class DrugInteractionRequest(BaseModel):
    drugs: List[str] = Field(default_factory=list)


class TriageRequest(BaseModel):
    symptoms: List[str] = Field(..., min_length=1)
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[str] = None
    pregnant: Optional[bool] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    patient_context: Optional[Dict[str, Any]] = None
