from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.database.db_manager import get_db
from backend.services.clinical_service import ClinicalService

router = APIRouter(prefix="/clinical", tags=["Clinical Support"])

@router.get("/guidelines")
def get_guidelines(category: str = None, db: Session = Depends(get_db)):
    try:
        return ClinicalService.get_guidelines(db, category)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/drugs")
def search_drugs(query: str, db: Session = Depends(get_db)):
    try:
        return ClinicalService.search_drugs(db, query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/drugs/interact")
def check_interactions(request: Dict[str, List[str]]):
    try:
        drugs = request.get("drugs", [])
        if not drugs:
            raise HTTPException(status_code=400, detail="No drugs provided")
        return ClinicalService.check_interactions(drugs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/protocols")
def get_protocols(condition: str):
    try:
        return ClinicalService.get_protocols(condition)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cds")
def clinical_decision_support(request: Dict[str, Any]):
    try:
        symptoms = request.get("symptoms", [])
        context = {k: v for k, v in request.items() if k != "symptoms"}
        return ClinicalService.cds_recommendation(symptoms, context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/triage")
def triage_assessment(request: Dict[str, Any]):
    try:
        symptoms = request.get("symptoms", [])
        context = {k: v for k, v in request.items() if k != "symptoms"}
        return ClinicalService.triage_assessment(symptoms, context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
