"""
Health metric routes — /metrics
Blueprint: health_router
"""

import io
import csv
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.api.models.request_models import (
    HealthMetricRequest, AnalyzeVitalsRequest, AnalyzeSymptomsRequest
)
from backend.api.models.response_models import (
    HealthMetricOut, VitalCheckResponse, SymptomAnalysisResponse, SuccessResponse
)
from backend.database.db_manager import db_manager
from backend.core.health_analyzer import health_analyzer
from backend.utils.logger import get_logger

logger = get_logger(__name__)
health_router = APIRouter(prefix="/metrics", tags=["Health Metrics"])


@health_router.post(
    "",
    response_model=SuccessResponse,
    summary="Save a health metric entry",
)
async def save_metric(request: HealthMetricRequest):
    try:
        entry_id = db_manager.save_health_metric(
            metric_type=request.metric_type,
            value=request.value,
            unit=request.unit,
            notes=request.notes or "",
        )
        # Run automatic vital check
        check = health_analyzer.check_vitals(request.metric_type, request.value)
        msg = f"Saved entry #{entry_id}. Vitals check: {check['status']} — {check['message']}"
        return SuccessResponse(success=True, message=msg)
    except Exception as exc:
        logger.error("Save metric error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@health_router.get(
    "",
    response_model=List[HealthMetricOut],
    summary="Get health metric entries",
)
async def get_metrics(
    metric_type: Optional[str] = Query(None),
    start_date:  Optional[str] = Query(None),
    end_date:    Optional[str] = Query(None),
    limit:       int           = Query(200, ge=1, le=1000),
):
    entries = db_manager.get_health_metrics(
        metric_type=metric_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return [HealthMetricOut(**e) for e in entries]


@health_router.get(
    "/export",
    summary="Export health metrics as CSV",
)
async def export_metrics(metric_type: Optional[str] = Query(None)):
    """Download all health metric entries as a CSV file."""
    entries = db_manager.get_health_metrics(metric_type=metric_type, limit=10000)
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
async def delete_metric(entry_id: int):
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
