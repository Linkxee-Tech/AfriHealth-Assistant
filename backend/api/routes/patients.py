"""
Patient Management API Routes — /patients and /visits
Blueprint: patients_router
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Any

from backend.database.db_manager import db_manager
from backend.core.health_analyzer import health_analyzer
from backend.api.dependencies.auth import get_current_user
from backend.utils.logger import get_logger

logger = get_logger(__name__)
patients_router = APIRouter(prefix="/patients", tags=["Patient Management"])

@patients_router.get("", summary="Get all patients list")
async def list_patients(search: str = Query(None), limit: int = Query(100), current_user = Depends(get_current_user)):
    return db_manager.get_patients(search=search, limit=limit)

@patients_router.post("", summary="Register new patient")
async def register_patient(payload: dict, current_user = Depends(get_current_user)):
    try:
        patient_id = db_manager.create_patient(payload)
        return {"success": True, "patient_id": patient_id, "message": "Patient registered successfully"}
    except Exception as e:
        logger.error(f"Error registering patient: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@patients_router.get("/{patient_id}", summary="Get patient details")
async def get_patient_details(patient_id: int, current_user = Depends(get_current_user)):
    patient = db_manager.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

@patients_router.put("/{patient_id}", summary="Update patient information")
async def update_patient(patient_id: int, payload: dict, current_user = Depends(get_current_user)):
    success = db_manager.update_patient(patient_id, payload)
    if not success:
        raise HTTPException(status_code=404, detail="Patient not found or update failed")
    return {"success": True, "message": "Patient updated successfully"}

@patients_router.delete("/{patient_id}", summary="Delete patient")
async def delete_patient(patient_id: int, current_user = Depends(get_current_user)):
    success = db_manager.delete_patient(patient_id)
    if not success:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"success": True, "message": "Patient deleted successfully"}

@patients_router.get("/{patient_id}/visits", summary="Get patient visit history")
async def list_patient_visits(patient_id: int, current_user = Depends(get_current_user)):
    return db_manager.get_patient_visits(patient_id)

@patients_router.post("/{patient_id}/visits", summary="Add new visit record")
async def add_patient_visit(patient_id: int, payload: dict, current_user = Depends(get_current_user)):
    payload["patient_id"] = patient_id
    
    # ⭐ Bonus: AI Auto-Complete Diagnosis 
    # If chief complaint is provided and diagnosis is empty, generate one
    chief_complaint = payload.get("chief_complaint", "")
    if chief_complaint and not payload.get("ai_suggestions"):
        try:
            # We use the advanced triage logic
            triage_result = health_analyzer.triage_symptoms([chief_complaint])
            ai_suggestions = triage_result.get("recommendation", "")
            if "clinical_decision_support" in triage_result:
                chw_plan = triage_result["clinical_decision_support"].get("chw_action_plan", "")
                ai_suggestions += f"\nCHW Plan: {chw_plan}"
            payload["ai_suggestions"] = ai_suggestions
        except Exception as e:
            logger.warning(f"AI diagnosis generation failed: {e}")
            payload["ai_suggestions"] = "AI Diagnosis unavailable."

    try:
        visit_id = db_manager.create_visit(payload)
        return {"success": True, "visit_id": visit_id, "message": "Visit recorded successfully"}
    except Exception as e:
        logger.error(f"Error adding visit: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Standalone Visit Routes
visits_router = APIRouter(prefix="/visits", tags=["Visit Management"])

@visits_router.get("/{visit_id}", summary="Get visit details")
async def get_visit_details(visit_id: int, current_user = Depends(get_current_user)):
    visit = db_manager.get_visit(visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    return visit
