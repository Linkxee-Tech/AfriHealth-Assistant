from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.database.models import ClinicalGuideline, Drug
from backend.core.gemini_integration import gemini_client
from backend.core.health_analyzer import health_analyzer
import logging
import math

logger = logging.getLogger(__name__)

class ClinicalService:
    @staticmethod
    def get_guidelines(db: Session, category: str = None, search: str = None) -> List[Dict[str, Any]]:
        query = db.query(ClinicalGuideline)
        if category:
            query = query.filter(ClinicalGuideline.category == category)
        if search:
            term = f"%{search}%"
            query = query.filter((ClinicalGuideline.title.ilike(term)) | (ClinicalGuideline.content.ilike(term)) | (ClinicalGuideline.source.ilike(term)))
        return [{"id": g.id, "title": g.title, "category": g.category, "content": g.content, "source": g.source} for g in query.all()]

    @staticmethod
    def search_drugs(db: Session, query: str) -> List[Dict[str, Any]]:
        drugs = db.query(Drug).filter(Drug.name.ilike(f"%{query}%")).all()
        return [{"id": d.id, "name": d.name, "category": d.category, "dosage_info": d.dosage_info, "side_effects": d.side_effects, "contraindications": d.contraindications} for d in drugs]

    @staticmethod
    def check_interactions(drugs: List[str]) -> Dict[str, Any]:
        """Run deterministic local checks first, then optionally enrich online."""
        local_result = health_analyzer.check_medication_interactions(drugs)
        if local_result["interactions"] or not gemini_client.is_configured:
            return local_result
        return gemini_client.check_drug_interaction(drugs)

    @staticmethod
    def get_protocols(condition: str) -> Dict[str, Any]:
        return health_analyzer.get_treatment_protocol(condition)

    @staticmethod
    def cds_recommendation(symptoms: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        if not gemini_client.is_configured:
            local = health_analyzer.triage_symptoms(symptoms, context)
            return {
                "possible_conditions": [],
                "recommendations": [local.get("recommendation") or local.get("advice") or "Seek clinician review."],
                "risk_factors": local.get("clinical_decision_support", {}).get("identified_risk_factors", []),
                "urgency": str(local.get("urgency") or local.get("severity") or "unknown").lower(),
                "source": "local deterministic triage; no cloud model configured",
            }
        return gemini_client.clinical_decision_support(symptoms, context)

    @staticmethod
    def triage_assessment(symptoms: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        if not gemini_client.is_configured:
            local = health_analyzer.triage_symptoms(symptoms, context)
            cds = local.get("clinical_decision_support", {})
            return {"urgency": local.get("urgency") or local.get("severity") or "Medium",
                    "advice": local.get("advice") or local.get("recommendation") or "Seek clinical review.",
                    "do_not": local.get("do_not", []),
                    "identified_risk_factors": cds.get("identified_risk_factors", []),
                    "epidemiological_flags": cds.get("epidemiological_flags", []),
                    "source": "local deterministic triage; no cloud model configured"}
        return gemini_client.generate_triage(symptoms, context)

    @staticmethod
    def calculate_dose(drug_name: str, patient_weight: float, age: int) -> Dict[str, Any]:
        if patient_weight <= 0 or age < 0:
            raise ValueError("Weight must be positive and age cannot be negative")
        return {"drug": drug_name, "status": "clinician_review_required", "recommended_dose": None,
                "safety_note": "No generic dose is issued. Confirm indication, formulation, age/weight, renal/hepatic function, pregnancy, allergies, and current local protocol before prescribing."}

    @staticmethod
    def calculate_bmi(height_cm: float, weight_kg: float) -> Dict[str, Any]:
        if height_cm <= 0 or weight_kg <= 0:
            raise ValueError("Height and weight must be positive")
        bmi = weight_kg / ((height_cm / 100) ** 2)
        category = "underweight" if bmi < 18.5 else "normal" if bmi < 25 else "overweight" if bmi < 30 else "obesity"
        return {"bmi": round(bmi, 2), "category": category}

    @staticmethod
    def calculate_egfr(creatinine_mg_dl: float, age: int, sex: str = "female") -> Dict[str, Any]:
        if creatinine_mg_dl <= 0 or age <= 0:
            raise ValueError("Creatinine and age must be positive")
        # 2021 CKD-EPI creatinine equation; report as estimate, not a diagnosis.
        k = 0.7 if str(sex).lower().startswith("f") else 0.9
        alpha = -0.241 if str(sex).lower().startswith("f") else -0.302
        egfr = 142 * min(creatinine_mg_dl / k, 1) ** alpha * max(creatinine_mg_dl / k, 1) ** -1.200 * (0.9938 ** age) * (1.012 if str(sex).lower().startswith("f") else 1)
        return {"egfr": round(egfr, 1), "unit": "mL/min/1.73m²", "note": "Estimate only; interpret with a qualified clinician and local laboratory context."}

    @staticmethod
    def vaccination_schedule(age_years: float) -> List[Dict[str, str]]:
        age = max(0, age_years)
        schedule = [{"vaccine": "BCG", "timing": "Birth", "status": "review record"}, {"vaccine": "Polio", "timing": "Birth and infant series", "status": "review record"}, {"vaccine": "Measles-containing vaccine", "timing": "Infancy according to national schedule", "status": "review record"}]
        if age >= 9:
            schedule.append({"vaccine": "Tetanus-containing booster", "timing": "Use national schedule", "status": "review record"})
        return schedule

    @staticmethod
    def generate_referral(patient_context: Dict[str, Any], reason: str) -> str:
        if not gemini_client.is_configured:
            return f"[Offline Mode] Referral for {reason}. Patient context: {patient_context}"
        prompt = f"Write a professional medical referral letter for a patient. Context: {patient_context}. Reason for referral: {reason}"
        return gemini_client.generate(prompt)
