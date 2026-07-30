from backend.database.db_manager import DatabaseManager
from backend.services.patient_service import PatientService


def test_patient_service_register_and_visit(tmp_path):
    manager = DatabaseManager(str(tmp_path / "patients.sqlite"))
    manager.init_tables()
    with manager.get_session() as db:
        patient = PatientService.register_patient(db, {"first_name": "Amina", "last_name": "Okafor"})
        assert patient.mrn.startswith("AH-")
        visit = PatientService.add_visit(db, {"patient_id": patient.id, "chief_complaint": "fever"})
        assert PatientService.get_visits(db, patient.id)[0].id == visit.id

