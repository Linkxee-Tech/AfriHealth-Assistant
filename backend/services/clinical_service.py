from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.database.models import ClinicalGuideline, Drug
from backend.core.gemini_integration import gemini_client
import logging

logger = logging.getLogger(__name__)

class ClinicalService:
    @staticmethod
    def get_guidelines(db: Session, category: str = None) -> List[Dict[str, Any]]:
        query = db.query(ClinicalGuideline)
        if category:
            query = query.filter(ClinicalGuideline.category == category)
        return [{"id": g.id, "title": g.title, "category": g.category, "content": g.content, "source": g.source} for g in query.all()]

    @staticmethod
    def search_drugs(db: Session, query: str) -> List[Dict[str, Any]]:
        drugs = db.query(Drug).filter(Drug.name.ilike(f"%{query}%")).all()
        return [{"id": d.id, "name": d.name, "category": d.category, "dosage_info": d.dosage_info, "side_effects": d.side_effects, "contraindications": d.contraindications} for d in drugs]

    @staticmethod
    def check_interactions(drugs: List[str]) -> Dict[str, Any]:
        """Uses Gemini to check for drug interactions if the local DB doesn't have exact combinations."""
        if not gemini_client.is_configured:
            return {"interactions": ["(Offline Fallback) AI interaction check disabled."], "notes": ["Please consult your local drug formulary."], "severity": "unknown"}
        return gemini_client.check_drug_interaction(drugs)

    @staticmethod
    def get_protocols(condition: str) -> Dict[str, Any]:
        """Mock protocol retrieval - normally this would search the RAG knowledge base."""
        return {
            "condition": condition,
            "protocol": [
                f"Assess patient for severe {condition} symptoms.",
                "Check vitals (BP, HR, Temp, SpO2).",
                "Consult WHO guidelines for recommended first-line treatment.",
                "Ensure hydration and rest."
            ],
            "references": ["WHO Guidelines 2024", "National Treatment Protocol"]
        }

    @staticmethod
    def cds_recommendation(symptoms: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        if not gemini_client.is_configured:
            return {"possible_conditions": ["(Offline) Pending AI connection"], "recommendations": ["(Offline) Monitor symptoms and rest."], "risk_factors": [], "urgency": "low"}
        return gemini_client.clinical_decision_support(symptoms, context)

    @staticmethod
    def triage_assessment(symptoms: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        if not gemini_client.is_configured:
            return {"urgency": "Medium", "advice": "(Offline) Monitor and consult clinic if symptoms worsen.", "do_not": [], "identified_risk_factors": [], "epidemiological_flags": []}
        return gemini_client.generate_triage(symptoms, context)

    @staticmethod
    def calculate_dose(drug_name: str, patient_weight: float, age: int) -> Dict[str, Any]:
        # Simplified dose calculator
        return {"drug": drug_name, "recommended_dose": f"{patient_weight * 2}mg", "frequency": "twice daily"}

    @staticmethod
    def generate_referral(patient_context: Dict[str, Any], reason: str) -> str:
        if not gemini_client.is_configured:
            return f"[Offline Mode] Referral for {reason}. Patient context: {patient_context}"
        prompt = f"Write a professional medical referral letter for a patient. Context: {patient_context}. Reason for referral: {reason}"
        return gemini_client.generate(prompt)
