from backend.services.clinical_service import ClinicalService


def test_clinical_calculators_are_deterministic_and_safe():
    assert ClinicalService.calculate_bmi(170, 70)["category"] == "normal"
    assert ClinicalService.calculate_egfr(1.0, 40)["egfr"] > 0
    dose = ClinicalService.calculate_dose("amoxicillin", 70, 40)
    assert dose["recommended_dose"] is None
    assert dose["status"] == "clinician_review_required"

