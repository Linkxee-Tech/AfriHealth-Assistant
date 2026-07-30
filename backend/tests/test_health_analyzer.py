from backend.core.health_analyzer import health_analyzer


def test_vital_ranges_and_emergency_triage():
    assert health_analyzer.check_vitals("Heart Rate", "72")["status"] == "normal"
    assert health_analyzer.check_vitals("Heart Rate", "160")["urgency"] in {"High", "Emergency"}
    result = health_analyzer.analyze_symptoms(["chest pain", "difficulty breathing"])
    assert result["urgency"] == "Emergency"

