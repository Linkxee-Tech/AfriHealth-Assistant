"""
Patient Management API Routes — /patients and /visits
Blueprint: patients_router
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Response
from typing import List, Dict, Any

from backend.database.db_manager import db_manager
from backend.core.health_analyzer import health_analyzer
from backend.api.dependencies.auth import get_current_user
from backend.services.pdf_export import generate_patient_summary_pdf
from backend.utils.logger import get_logger

logger = get_logger(__name__)
patients_router = APIRouter(prefix="/patients", tags=["Patient Management"])

@patients_router.get("", summary="Get all patients list")
async def list_patients(search: str = Query(None), limit: int = Query(100), current_user = Depends(get_current_user)):
    return db_manager.get_patients(search=search, limit=limit, user_id=current_user.id)

@patients_router.post("", summary="Register new patient")
async def register_patient(payload: dict, current_user = Depends(get_current_user)):
    try:
        patient_id = db_manager.create_patient(payload, user_id=current_user.id)
        return {"success": True, "patient_id": patient_id, "message": "Patient registered successfully"}
    except Exception as e:
        logger.error(f"Error registering patient: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@patients_router.get("/search", summary="Search patients")
async def search_patients(search: str = Query(None), limit: int = Query(100), current_user = Depends(get_current_user)):
    return db_manager.get_patients(search=search, limit=limit, user_id=current_user.id)

@patients_router.get("/{patient_id}", summary="Get patient details")
async def get_patient_details(patient_id: int, current_user = Depends(get_current_user)):
    patient = db_manager.get_patient(patient_id, user_id=current_user.id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

@patients_router.get("/{patient_id}/export/pdf", summary="Export patient summary as PDF")
async def export_patient_pdf(patient_id: int, current_user = Depends(get_current_user)):
    with db_manager.get_session() as session:
        from backend.database.models import Patient
        patient_record = session.query(Patient).filter(
            Patient.id == patient_id, 
            Patient.user_id == current_user.id
        ).first()
        
        if not patient_record:
            raise HTTPException(status_code=404, detail="Patient not found")
            
        visits = db_manager.get_patient_visits(patient_id, user_id=current_user.id)
        # Assuming health metrics might be added later, for now we pass an empty list
        # or we could fetch them if they exist.
        metrics = []
        try:
            metrics = db_manager.get_health_entries(limit=5, patient_id=patient_id)
        except Exception:
            pass # Ignore if get_health_entries isn't fully robust
            
        pdf_bytes = generate_patient_summary_pdf(patient_record, visits, metrics)
        
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=patient_{patient_id}_summary.pdf"}
    )

@patients_router.put("/{patient_id}", summary="Update patient information")
async def update_patient(patient_id: int, payload: dict, current_user = Depends(get_current_user)):
    success = db_manager.update_patient(patient_id, payload, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Patient not found or update failed")
    return {"success": True, "message": "Patient updated successfully"}

@patients_router.delete("/{patient_id}", summary="Delete patient")
async def delete_patient(patient_id: int, current_user = Depends(get_current_user)):
    success = db_manager.delete_patient(patient_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"success": True, "message": "Patient deleted successfully"}

@patients_router.get("/{patient_id}/visits", summary="Get patient visit history")
async def list_patient_visits(patient_id: int, current_user = Depends(get_current_user)):
    return db_manager.get_patient_visits(patient_id, user_id=current_user.id)

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
        visit_id = db_manager.create_visit(payload, user_id=current_user.id)
        return {"success": True, "visit_id": visit_id, "message": "Visit recorded successfully"}
    except Exception as e:
        logger.error(f"Error adding visit: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@patients_router.get("/{patient_id}/export", summary="Export patient record")
async def export_patient(patient_id: int, current_user = Depends(get_current_user)):
    record = db_manager.export_patient(patient_id, user_id=current_user.id)
    if not record:
        raise HTTPException(status_code=404, detail="Patient not found")
    return record


@patients_router.get("/{patient_id}/export/pdf", summary="Export patient record as PDF")
async def export_patient_pdf(patient_id: int, current_user = Depends(get_current_user)):
    import io
    from fastapi.responses import StreamingResponse
    from backend.services.export_service import export_service

    record = db_manager.export_patient(patient_id, user_id=current_user.id)
    if not record:
        raise HTTPException(status_code=404, detail="Patient not found")
    metrics = db_manager.get_health_entries(limit=1000, user_id=current_user.id, patient_id=patient_id)
    patient = record["patient"]
    summary = patient.get("medical_history") or patient.get("notes") or "No clinical summary recorded."
    pdf = export_service.export_clinical_report_pdf(patient, metrics, summary)
    filename = f"patient-{patient.get('mrn') or patient_id}-report.pdf"
    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

# Standalone Visit Routes
visits_router = APIRouter(prefix="/visits", tags=["Visit Management"])

@visits_router.get("/{visit_id}", summary="Get visit details")
async def get_visit_details(visit_id: int, current_user = Depends(get_current_user)):
    visit = db_manager.get_visit(visit_id, user_id=current_user.id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    return visit

@visits_router.put("/{visit_id}", summary="Update visit details")
async def update_visit(visit_id: int, payload: dict, current_user = Depends(get_current_user)):
    if not db_manager.update_visit(visit_id, payload, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="Visit not found or update failed")
    return {"success": True, "message": "Visit updated successfully"}

@visits_router.get("/{visit_id}/prescription/pdf", summary="Export visit prescription as PDF")
async def export_prescription_pdf(visit_id: int, current_user = Depends(get_current_user)):
    from fastapi.responses import StreamingResponse
    from backend.services.export_service import export_service
    visit = db_manager.get_visit(visit_id, user_id=current_user.id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    patient = db_manager.get_patient(visit["patient_id"], user_id=current_user.id) or {}
    medications = visit.get("medications") or "No medication recorded."
    summary = f"Prescription/plan for {patient.get('first_name', '')} {patient.get('last_name', '')}\n\n{medications}\n\nClinical note: Verify every medicine, dose, route, duration, allergy, pregnancy, and renal/hepatic consideration before use."
    pdf = export_service.export_clinical_report_pdf(patient, [], summary)
    return StreamingResponse(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="prescription-{visit_id}.pdf"'})
