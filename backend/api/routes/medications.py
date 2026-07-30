"""
Medication Reminder routes — CRUD for medication schedules.
"""
import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from backend.api.dependencies.auth import get_current_user
from backend.database.db_manager import db_manager
from backend.utils.logger import get_logger

logger = get_logger(__name__)
medications_router = APIRouter(prefix="/medications", tags=["Medications"])


class MedicationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Medication name")
    dosage: str = Field(..., min_length=1, description="Dosage e.g. '500mg'")
    frequency: str = Field(..., description="e.g. 'Twice daily', 'Every 8 hours'")
    times: List[str] = Field(default_factory=list, description="Times of day e.g. ['08:00', '20:00']")
    start_date: Optional[str] = Field(None, description="Start date YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="End date YYYY-MM-DD")
    notes: Optional[str] = Field(None, description="Additional instructions")
    patient_id: Optional[int] = Field(None, description="Associated patient ID")


@medications_router.post("", summary="Add a medication reminder")
async def add_medication(request: MedicationRequest, current_user=Depends(get_current_user)):
    try:
        med_id = db_manager.add_medication(
            user_id=current_user.id,
            name=request.name,
            dosage=request.dosage,
            frequency=request.frequency,
            times=json.dumps(request.times),
            start_date=request.start_date,
            end_date=request.end_date,
            notes=request.notes,
            patient_id=request.patient_id,
        )
        return {"success": True, "id": med_id, "message": f"Medication '{request.name}' added"}
    except Exception as exc:
        logger.exception("Failed to add medication")
        raise HTTPException(status_code=500, detail=str(exc))


@medications_router.get("", summary="Get all medication reminders for current user")
async def get_medications(patient_id: Optional[int] = Query(None, description="Filter by patient ID"), current_user=Depends(get_current_user)):
    try:
        meds = db_manager.get_medications(user_id=current_user.id)
        if patient_id is not None:
            meds = [m for m in meds if m.get("patient_id") == patient_id]
        return {"medications": meds, "count": len(meds)}
    except Exception as exc:
        logger.exception("Failed to get medications")
        raise HTTPException(status_code=500, detail=str(exc))


@medications_router.delete("/{med_id}", summary="Delete a medication reminder")
async def delete_medication(med_id: int, current_user=Depends(get_current_user)):
    try:
        db_manager.delete_medication(med_id=med_id, user_id=current_user.id)
        return {"success": True, "message": "Medication reminder deleted"}
    except Exception as exc:
        logger.exception("Failed to delete medication")
        raise HTTPException(status_code=500, detail=str(exc))
