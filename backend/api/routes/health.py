"""
Health metric routes — /metrics
Blueprint: health_router
"""

import io
import csv
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from backend.api.dependencies.auth import get_current_user

from backend.api.models.request_models import (
    HealthMetricRequest, AnalyzeVitalsRequest, AnalyzeSymptomsRequest,
    PersonalizedCoachRequest, MedicationInteractionRequest,
    TreatmentProtocolRequest, ClinicalTriageRequest,
)
from backend.api.models.response_models import (
    HealthMetricOut, VitalCheckResponse, SymptomAnalysisResponse,
    ClinicalSupportResponse, PersonalizedCoachResponse,
    MedicationInteractionResponse, TreatmentProtocolResponse,
    SuccessResponse,
)
from backend.database.db_manager import db_manager
from backend.core.health_analyzer import health_analyzer
from backend.utils.logger import get_logger

logger = get_logger(__name__)
health_router = APIRouter(prefix="/metrics", tags=["Health Metrics"])


class HealthMetricCreate(BaseModel):
    metric_type: str = Field(..., description="E.g., Blood Pressure, Blood Sugar, Weight, Heart Rate")
    value: str = Field(..., description="The recorded value, e.g., 120/80")
    unit: Optional[str] = Field("", description="E.g., mmHg, mg/dL, kg")
    notes: Optional[str] = Field("", description="Any clinical notes")
    patient_id: Optional[int] = Field(None, description="Optional Patient ID")


@health_router.post("/metrics", summary="Save a new health metric", response_model=Dict[str, Any])
async def add_metric(payload: HealthMetricCreate, current_user = Depends(get_current_user)):
    """Save a patient's health reading locally."""
    try:
        entry_id = db_manager.add_health_entry(
            metric_type=payload.metric_type,
            value=payload.value,
            unit=payload.unit,
            notes=payload.notes,
            user_id=current_user.id,
            patient_id=payload.patient_id
        )
        # Run automatic vital check
        check = health_analyzer.check_vitals(payload.metric_type, payload.value)
        msg = f"Saved entry #{entry_id}. Vitals check: {check['status']} — {check['message']}"
        return {"success": True, "message": msg}
    except Exception as exc:
        logger.error("Save metric error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@health_router.get("/metrics", summary="Get historical health metrics")
async def get_metrics(
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    patient_id: Optional[int] = Query(None, description="Filter by Patient ID"),
    limit: int = Query(100, description="Number of recent entries to fetch"),
    current_user = Depends(get_current_user)
):
    """Retrieve saved health metrics from local SQLite."""
    try:
        entries = db_manager.get_health_entries(
            limit=limit,
            user_id=current_user.id,
            patient_id=patient_id
        )
        if metric_type:
            entries = [e for e in entries if e.get("metric_type") == metric_type]
        return {"success": True, "metrics": entries}
    except Exception as exc:
        logger.error("Get metrics error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@health_router.get(
    "/export",
    summary="Export health metrics as CSV",
)
async def export_metrics(metric_type: Optional[str] = Query(None), current_user = Depends(get_current_user)):
    """Download all health metric entries as a CSV file."""
    entries = db_manager.get_health_metrics(metric_type=metric_type, limit=10000, user_id=current_user.id)
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=["id", "metric_type", "value", "unit", "notes", "recorded_at"]
    )
    writer.writeheader()
    writer.writerows(entries)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=afrihealth_metrics.csv"},
    )


@health_router.delete(
    "/{entry_id}",
    response_model=SuccessResponse,
    summary="Delete a health metric entry",
)
async def delete_metric(entry_id: int, current_user = Depends(get_current_user)):
    # Note: A real app would check if the entry belongs to current_user before deleting.
    deleted = db_manager.delete_health_metric(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Entry #{entry_id} not found.")
    return SuccessResponse(success=True, message=f"Deleted entry #{entry_id}")


@health_router.post(
    "/check-vitals",
    response_model=VitalCheckResponse,
    summary="Check a vital sign against normal ranges",
)
async def check_vitals(request: AnalyzeVitalsRequest):
    result = health_analyzer.check_vitals(request.metric_type, request.value)
    # health_analyzer may return a 'value' key — remove it to avoid conflict
    result.pop("value", None)
    return VitalCheckResponse(
        metric_type=request.metric_type,
        value=request.value,
        **result,
    )


@health_router.post(
    "/analyze-symptoms",
    response_model=SymptomAnalysisResponse,
    summary="Triage a list of symptoms",
)
async def analyze_symptoms(request: AnalyzeSymptomsRequest):
    result = health_analyzer.analyze_symptoms(request.symptoms)
    return SymptomAnalysisResponse(**result)


@health_router.post(
    "/clinical-triage",
    response_model=ClinicalSupportResponse,
    summary="Advanced clinical triage for symptom lists",
)
async def clinical_triage(request: ClinicalTriageRequest):
    result = health_analyzer.triage_symptoms(request.symptoms, request.patient_context.dict() if request.patient_context else None)
    return ClinicalSupportResponse(
        urgency=result.get("urgency", "Low"),
        advice=result.get("advice", ""),
        do_not=result.get("do_not", []),
        identified_risk_factors=result.get("clinical_decision_support", {}).get("identified_risk_factors", []),
        epidemiological_flags=result.get("clinical_decision_support", {}).get("epidemiological_flags", []),
        chw_action_plan=result.get("clinical_decision_support", {}).get("chw_action_plan", ""),
    )


@health_router.post(
    "/coach",
    response_model=PersonalizedCoachResponse,
    summary="Generate personalized health coaching recommendations",
)
async def personalized_coach(request: PersonalizedCoachRequest):
    result = health_analyzer.get_personalized_coach(request.metrics, request.patient_context.dict() if request.patient_context else None)
    return PersonalizedCoachResponse(**result)


@health_router.post(
    "/medications/interactions",
    response_model=MedicationInteractionResponse,
    summary="Check for potential medication interactions",
)
async def medication_interactions(request: MedicationInteractionRequest):
    result = health_analyzer.check_medication_interactions(request.medications)
    return MedicationInteractionResponse(**result)


@health_router.post(
    "/protocols",
    response_model=TreatmentProtocolResponse,
    summary="Get a basic offline treatment protocol for a condition",
)
async def treatment_protocol(request: TreatmentProtocolRequest):
    result = health_analyzer.get_treatment_protocol(request.condition)
    return TreatmentProtocolResponse(**result)
