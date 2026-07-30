from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.database.db_manager import get_db
from backend.database.models import ClinicalGuideline
from backend.services.clinical_service import ClinicalService
from backend.api.dependencies.auth import get_current_user
from backend.api.models.request_models import ClinicalCDSRequest, DrugInteractionRequest, TriageRequest

router = APIRouter(prefix="/clinical", tags=["Clinical Support"])

class CalculatorRequest(BaseModel):
    height_cm: float = 0
    weight_kg: float = 0
    creatinine_mg_dl: float = 0
    age: int = 0
    sex: str = "female"

class DoseRequest(BaseModel):
    drug_name: str
    patient_weight: float
    age: int

@router.get("/guidelines")
def get_guidelines(category: str = None, query: str = None, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        return ClinicalService.get_guidelines(db, category, query)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/guidelines/{guideline_id}/pdf")
def download_guideline_pdf(guideline_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    from fastapi.responses import StreamingResponse
    from backend.services.export_service import export_service
    guideline = db.query(ClinicalGuideline).filter(ClinicalGuideline.id == guideline_id).first()
    if not guideline:
        raise HTTPException(status_code=404, detail="Guideline not found")
    pdf = export_service.export_clinical_report_pdf(
        {"first_name": guideline.title, "last_name": "", "mrn": "reference"},
        [],
        f"{guideline.content}\n\nSource: {guideline.source or 'Not specified'}",
    )
    return StreamingResponse(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="guideline-{guideline_id}.pdf"'})

@router.get("/drugs")
def search_drugs(query: str = Query(""), db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        return ClinicalService.search_drugs(db, query)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/drugs/interact")
def check_interactions(request: DrugInteractionRequest, current_user = Depends(get_current_user)):
    try:
        drugs = request.drugs
        if not drugs:
            raise HTTPException(status_code=400, detail="No drugs provided")
        return ClinicalService.check_interactions(drugs)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/protocols")
def get_protocols(condition: str, current_user = Depends(get_current_user)):
    try:
        return ClinicalService.get_protocols(condition)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cds")
def clinical_decision_support(request: ClinicalCDSRequest, current_user = Depends(get_current_user)):
    try:
        symptoms = request.symptoms
        context = {**(request.patient_context or {}), **request.context, "age": request.age, "gender": request.gender, "pregnant": request.pregnant}
        return ClinicalService.cds_recommendation(symptoms, context)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/triage")
def triage_assessment(request: TriageRequest, current_user = Depends(get_current_user)):
    try:
        symptoms = request.symptoms
        context = {**(request.patient_context or {}), **request.context, "age": request.age, "gender": request.gender, "pregnant": request.pregnant}
        return ClinicalService.triage_assessment(symptoms, context)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calculators/bmi")
def bmi(request: CalculatorRequest, current_user = Depends(get_current_user)):
    try:
        return ClinicalService.calculate_bmi(request.height_cm, request.weight_kg)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

@router.post("/calculators/egfr")
def egfr(request: CalculatorRequest, current_user = Depends(get_current_user)):
    try:
        return ClinicalService.calculate_egfr(request.creatinine_mg_dl, request.age, request.sex)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

@router.post("/calculators/dose")
def dose(request: DoseRequest, current_user = Depends(get_current_user)):
    try:
        return ClinicalService.calculate_dose(request.drug_name, request.patient_weight, request.age)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

@router.get("/vaccinations")
def vaccinations(age_years: float = Query(0, ge=0, le=120), current_user = Depends(get_current_user)):
    return {"age_years": age_years, "schedule": ClinicalService.vaccination_schedule(age_years), "note": "Confirm the current national immunisation schedule with a health worker."}

@router.post("/referral")
def referral(request: Dict[str, Any], current_user = Depends(get_current_user)):
    reason = str(request.get("reason", "")).strip()
    if not reason:
        raise HTTPException(status_code=422, detail="Referral reason is required")
    return {"letter": ClinicalService.generate_referral(request.get("patient_context", {}), reason)}
