"""
Health Analyzer — rule-based vital signs checker and symptom analysis.
Provides structured assessments without LLM inference (fast, offline, deterministic).
LLM-based deeper analysis is layered on top by the chat/RAG engine.
"""

from typing import Dict, List, Optional
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Normal ranges (WHO / standard clinical references)
VITAL_RANGES = {
    "Heart Rate":               {"min": 60,  "max": 100, "unit": "bpm",   "emergency_low": 40,  "emergency_high": 150},
    "Blood Sugar":              {"min": 70,  "max": 140, "unit": "mg/dL", "emergency_low": 54,  "emergency_high": 250},
    "Weight":                   {"min": 0,   "max": 300, "unit": "kg",    "emergency_low": None,"emergency_high": None},
    "Temperature":              {"min": 36.1,"max": 37.2,"unit": "°C",    "emergency_low": 35.0,"emergency_high": 39.5},
    "Oxygen Saturation (SpO2)": {"min": 95,  "max": 100, "unit": "%",     "emergency_low": 90,  "emergency_high": None},
    "Sleep Hours":              {"min": 7,   "max": 9,   "unit": "hrs",   "emergency_low": None,"emergency_high": None},
}

URGENCY_LEVELS = ["Low", "Medium", "High", "Emergency"]


class HealthAnalyzer:
    """Analyzes health metrics and symptoms."""

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    def check_vitals(self, metric_type: str, value_str: str) -> Dict:
        """
        Check a single vital sign against normal ranges.
        Returns status, urgency, and advice.
        """
        if metric_type == "Blood Pressure":
            return self._check_blood_pressure(value_str)

        ranges = VITAL_RANGES.get(metric_type)
        if not ranges:
            return {"status": "unknown", "urgency": "Low",
                    "message": f"No reference range available for {metric_type}."}

        try:
            value = float(value_str.strip())
        except ValueError:
            return {"status": "parse_error", "urgency": "Low",
                    "message": f"Could not parse value '{value_str}' as a number."}

        emergency_high = ranges.get("emergency_high")
        emergency_low  = ranges.get("emergency_low")

        if emergency_high and value >= emergency_high:
            return {
                "status": "critical_high", "urgency": "Emergency",
                "message": f"{metric_type} of {value} {ranges['unit']} is dangerously high. "
                           "Seek emergency care immediately.",
                "value": value, "unit": ranges["unit"],
            }
        if emergency_low and value <= emergency_low:
            return {
                "status": "critical_low", "urgency": "Emergency",
                "message": f"{metric_type} of {value} {ranges['unit']} is dangerously low. "
                           "Seek emergency care immediately.",
                "value": value, "unit": ranges["unit"],
            }
        if value > ranges["max"]:
            return {
                "status": "high", "urgency": "Medium",
                "message": f"{metric_type} of {value} {ranges['unit']} is above the normal range "
                           f"({ranges['min']}–{ranges['max']} {ranges['unit']}). Consult a doctor.",
                "value": value, "unit": ranges["unit"],
            }
        if value < ranges["min"]:
            return {
                "status": "low", "urgency": "Medium",
                "message": f"{metric_type} of {value} {ranges['unit']} is below the normal range "
                           f"({ranges['min']}–{ranges['max']} {ranges['unit']}). Consult a doctor.",
                "value": value, "unit": ranges["unit"],
            }
        return {
            "status": "normal", "urgency": "Low",
            "message": f"{metric_type} of {value} {ranges['unit']} is within normal range. Good.",
            "value": value, "unit": ranges["unit"],
        }

    # ------------------------------------------------------------------
    def _check_blood_pressure(self, value_str: str) -> Dict:
        """Parse 'systolic/diastolic' format and classify BP."""
        try:
            parts = value_str.strip().split("/")
            if len(parts) != 2:
                raise ValueError("Expected systolic/diastolic format e.g. 120/80")
            systolic  = float(parts[0])
            diastolic = float(parts[1])
        except ValueError as exc:
            return {"status": "parse_error", "urgency": "Low",
                    "message": f"Blood Pressure parse error: {exc}. Use format '120/80'."}

        if systolic >= 180 or diastolic >= 120:
            return {"status": "hypertensive_crisis", "urgency": "Emergency",
                    "message": "Hypertensive crisis! Seek emergency care immediately."}
        if systolic >= 140 or diastolic >= 90:
            return {"status": "high", "urgency": "High",
                    "message": "High Blood Pressure (Stage 2 hypertension). See a doctor soon."}
        if systolic >= 130 or diastolic >= 80:
            return {"status": "elevated", "urgency": "Medium",
                    "message": "Elevated Blood Pressure (Stage 1 hypertension). Consult your doctor."}
        if systolic < 90 or diastolic < 60:
            return {"status": "low", "urgency": "Medium",
                    "message": "Low Blood Pressure. Monitor for dizziness. Consult a doctor."}
        return {"status": "normal", "urgency": "Low",
                "message": f"Blood Pressure {value_str} mmHg is within normal range."}

    # ------------------------------------------------------------------
    def analyze_symptoms(self, symptoms: List[str]) -> Dict:
        """
        Keyword-based triage for a list of symptom strings.
        Returns urgency level and first-aid guidance.
        """
        symptoms_lower = " ".join(symptoms).lower()

        emergency_keywords = [
            "chest pain", "can't breathe", "difficulty breathing", "unconscious",
            "stroke", "seizure", "severe bleeding", "not responding", "heart attack",
        ]
        high_keywords = [
            "high fever", "vomiting blood", "blood in stool", "severe headache",
            "vision loss", "sudden weakness", "confusion", "severe pain",
        ]
        medium_keywords = [
            "fever", "headache", "cough", "diarrhoea", "diarrhea",
            "vomiting", "rash", "joint pain", "malaria", "typhoid",
        ]

        if any(kw in symptoms_lower for kw in emergency_keywords):
            return {
                "urgency": "Emergency",
                "advice": "CALL EMERGENCY SERVICES NOW. Go to the nearest hospital immediately.",
                "do_not": ["Wait at home", "Take unverified medications", "Drive yourself"],
            }
        if any(kw in symptoms_lower for kw in high_keywords):
            return {
                "urgency": "High",
                "advice": "Seek medical attention TODAY. Do not delay going to a clinic or hospital.",
                "do_not": ["Self-medicate without guidance"],
            }
        if any(kw in symptoms_lower for kw in medium_keywords):
            return {
                "urgency": "Medium",
                "advice": "Monitor symptoms. Visit a healthcare provider within 24–48 hours "
                          "if symptoms worsen or do not improve.",
                "do_not": ["Ignore worsening symptoms"],
            }
        return {
            "urgency": "Low",
            "advice": "Symptoms appear mild. Rest, stay hydrated, and monitor. "
                      "Seek help if condition changes.",
            "do_not": [],
        }

    # ------------------------------------------------------------------
    def get_recommendations(self, metrics: List[Dict]) -> List[Dict]:
        """
        Run check_vitals on a list of metric dicts and return
        only those that need attention (non-normal status).
        """
        alerts = []
        for m in metrics:
            result = self.check_vitals(m.get("metric_type", ""), str(m.get("value", "")))
            if result.get("status") != "normal":
                result["metric_type"] = m.get("metric_type")
                alerts.append(result)
        return alerts


health_analyzer = HealthAnalyzer()
