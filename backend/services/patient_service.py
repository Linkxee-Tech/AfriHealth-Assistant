from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.database.models import Patient, Visit
from backend.utils.helpers import generate_mrn
import logging

logger = logging.getLogger(__name__)

class PatientService:
    @staticmethod
    def register_patient(db: Session, patient_data: Dict[str, Any]) -> Patient:
        patient_data = dict(patient_data)
        patient_data.setdefault("mrn", generate_mrn(db.query(Patient).count() + 1))
        patient = Patient(**patient_data)
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient

    @staticmethod
    def get_patient(db: Session, patient_id: int) -> Optional[Patient]:
        return db.query(Patient).filter(Patient.id == patient_id).first()

    @staticmethod
    def update_patient(db: Session, patient_id: int, updates: Dict[str, Any]) -> Optional[Patient]:
        patient = PatientService.get_patient(db, patient_id)
        if not patient:
            return None
        for key, value in updates.items():
            setattr(patient, key, value)
        db.commit()
        db.refresh(patient)
        return patient

    @staticmethod
    def delete_patient(db: Session, patient_id: int) -> bool:
        patient = PatientService.get_patient(db, patient_id)
        if not patient:
            return False
        db.delete(patient)
        db.commit()
        return True

    @staticmethod
    def search_patients(db: Session, query: str = None) -> List[Patient]:
        if query:
            return db.query(Patient).filter(
                (Patient.first_name.ilike(f"%{query}%")) | 
                (Patient.last_name.ilike(f"%{query}%")) |
                (Patient.mrn.ilike(f"%{query}%"))
            ).all()
        return db.query(Patient).all()

    @staticmethod
    def add_visit(db: Session, visit_data: Dict[str, Any]) -> Visit:
        visit = Visit(**visit_data)
        db.add(visit)
        db.commit()
        db.refresh(visit)
        return visit

    @staticmethod
    def get_visits(db: Session, patient_id: int) -> List[Visit]:
        return db.query(Visit).filter(Visit.patient_id == patient_id).all()

    @staticmethod
    def export_patient(db: Session, patient_id: int) -> Dict[str, Any]:
        patient = PatientService.get_patient(db, patient_id)
        if not patient:
            return {}
        visits = PatientService.get_visits(db, patient_id)
        return {
            "patient": {
                "mrn": patient.mrn,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "gender": patient.gender,
                "date_of_birth": str(patient.date_of_birth),
            },
            "visits": [{"visit_date": str(v.visit_date), "diagnosis": v.diagnosis} for v in visits]
        }
