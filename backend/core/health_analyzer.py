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

MEDICATION_INTERACTIONS = {
    frozenset(["aspirin", "ibuprofen"]): "Increased bleeding risk. Avoid using both without clinician advice.",
    frozenset(["warfarin", "ibuprofen"]): "High bleeding risk and unstable INR. Consult a doctor before combining.",
    frozenset(["metformin", "contrast dye"]): "Risk of lactic acidosis when using contrast dye with metformin. Notify your care provider.",
    frozenset(["amoxicillin", "methotrexate"]): "Methotrexate levels may rise with antibiotics, increasing toxicity risk.",
}

TREATMENT_PROTOCOLS = {
    "malaria": [
        "Confirm diagnosis with an RDT or microscopy.",
        "Administer artemisinin-based combination therapy (ACT) following national guidelines.",
        "Ensure hydration and follow-up in 24-48 hours.",
        "Refer to a clinician if symptoms worsen or signs of severe malaria appear.",
    ],
    "hypertension": [
        "Encourage lifestyle changes: reduce salt intake, increase physical activity, and stop smoking.",
        "Begin first-line antihypertensive therapy per local guidelines.",
        "Monitor blood pressure regularly and adjust medication as needed.",
        "Advise follow-up within 2-4 weeks for treatment response.",
    ],
    "diabetes": [
        "Advise dietary changes to manage blood sugar and encourage regular exercise.",
        "Start metformin unless contraindicated.",
        "Monitor fasting blood glucose and HbA1c per local protocol.",
        "Refer to a diabetes specialist for complications or poor control.",
    ],
    "pneumonia": [
        "Assess severity and oxygen saturation.",
        "Begin appropriate antibiotic therapy for community-acquired pneumonia.",
        "Provide supportive care including fluids and rest.",
        "Refer to hospital if respiratory distress or hypoxia is present.",
    ],
    "typhoid": [
        "Confirm diagnosis (Widal test, blood culture, or strong clinical features).",
        "Administer appropriate antibiotic therapy (e.g., Ciprofloxacin, Ceftriaxone, or Azithromycin based on local resistance).",
        "Provide supportive care: oral/intravenous rehydration and paracetamol for fever control.",
        "Monitor closely for complications: intestinal perforation, bleeding, or altered mental status (require urgent referral).",
        "Educate patient/family on food safety, hygiene, hand washing, and safe drinking water.",
    ],
    "cholera": [
        "Assess dehydration level immediately (None, Some, Severe).",
        "Begin immediate rehydration: Oral Rehydration Salts (ORS) for mild/moderate, IV fluids (Ringer's Lactate) for severe.",
        "Administer an appropriate antibiotic (e.g., Doxycycline or Azithromycin) to reduce fluid requirements and duration.",
        "Provide zinc supplementation for children under 5 years.",
        "Strict hygiene, quarantine protocols, and notify local health authorities immediately.",
    ],
    "dehydration": [
        "Assess severity: dry mouth, sunken eyes, skin pinch, low urine output.",
        "For mild to moderate dehydration, administer Oral Rehydration Salts (ORS) in small, frequent sips.",
        "For severe dehydration or inability to drink, initiate IV rehydration immediately.",
        "Address the underlying cause (e.g., diarrhea, vomiting, heat illness).",
    ],
}


class HealthAnalyzer:
    """Analyzes health metrics and symptoms."""

    def __init__(self):
        self.vital_ranges = VITAL_RANGES

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


    def get_personalized_coach(self, metrics: List[Dict], patient_context: Optional[Dict] = None) -> Dict:
        """
        Return personalised lifestyle and follow-up guidance based on metrics and patient context.
        """
        insights = []
        risk_alerts = []
        recommendations = []
        follow_up = []

        if patient_context:
            age = patient_context.get("age")
            if age is not None and age >= 65:
                insights.append("Age over 65 increases risk for chronic disease; monitor vitals more frequently.")
            if patient_context.get("pregnant"):
                insights.append("Pregnancy requires closer follow-up and regular antenatal care.")

        for metric in metrics:
            metric_type = metric.get("metric_type", "")
            value = str(metric.get("value", ""))
            advice = self.check_vitals(metric_type, value)
            if advice["urgency"] in {"High", "Emergency"}:
                risk_alerts.append(f"{metric_type}: {advice['message']}")
            if metric_type == "Sleep Hours":
                try:
                    sleep_hours = float(value)
                except (TypeError, ValueError):
                    sleep_hours = None
                if sleep_hours is not None and sleep_hours < 7:
                    recommendations.append("Increase sleep duration to 7-9 hours per night for better health.")
                elif sleep_hours is not None:
                    recommendations.append("Maintain your sleep routine and quality.")
            if metric_type == "Weight" and patient_context:
                height = patient_context.get("height_cm")
                weight = float(value) if value.replace('.', '', 1).isdigit() else None
                if height and weight:
                    bmi = weight / ((height / 100) ** 2)
                    if bmi >= 30:
                        risk_alerts.append("BMI indicates obesity. Review diet and exercise.")
                        recommendations.append("Aim for gradual weight loss through balanced meals and walking.")
                    elif bmi < 18.5:
                        recommendations.append("Increase caloric intake with nutritious foods to reach a healthy BMI.")
                    else:
                        recommendations.append("Your BMI is within a healthy range. Keep up your current habits.")

        if not recommendations:
            recommendations.append("Keep tracking your vitals and stay consistent with healthy habits.")

        follow_up.append("Review your metrics weekly and consult a clinician if any values remain abnormal.")
        follow_up.append("If you experience new high-risk symptoms, seek care immediately.")

        return {
            "insights": insights,
            "risk_alerts": risk_alerts,
            "recommendations": recommendations,
            "follow_up": follow_up,
        }


    def check_medication_interactions(self, medications: List[str]) -> Dict:
        """
        Return potential interactions for a list of medications.
        """
        meds_normalized = [m.strip().lower() for m in medications if m.strip()]
        interactions = []
        for combo, note in MEDICATION_INTERACTIONS.items():
            if combo.issubset(set(meds_normalized)):
                interactions.append(note)

        return {
            "interactions": interactions,
            "safe_to_continue": len(interactions) == 0,
            "notes": [
                "Consult a healthcare professional before changing any medication.",
                "This is not a substitute for a clinician review.",
            ],
        }


    def get_treatment_protocol(self, condition: str) -> Dict:
        """
        Return a basic standard treatment protocol for a common condition.
        """
        normalized = condition.strip().lower()
        protocol = TREATMENT_PROTOCOLS.get(normalized)
        if not protocol:
            return {
                "condition": condition,
                "protocol": [
                    "No offline treatment protocol available for this condition.",
                    "Refer to a qualified health worker or local clinical guideline.",
                ],
                "references": ["Use local WHO or national guideline references."],
            }
        return {
            "condition": condition,
            "protocol": protocol,
            "references": ["WHO guidelines", "Local national treatment protocol"],
        }


    def triage_symptoms(self, symptoms: List[str], patient_context: Dict = None) -> Dict:
        """
        [PHASE 3: Clinical Decision Support]
        Advanced triage logic generating a clinical summary intended for
        Community Health Workers (CHWs) or doctors.
        """
        logger.info(f"Running clinical triage on {len(symptoms)} symptoms...")
        
        # Merge basic analysis with advanced triage rules
        basic_analysis = self.analyze_symptoms(symptoms)
        
        risk_factors = []
        if patient_context:
            age = patient_context.get("age", 30)
            if age > 65 or age < 5:
                risk_factors.append("Vulnerable Age Group")
            if patient_context.get("pregnant", False):
                risk_factors.append("Pregnancy")
                basic_analysis["severity"] = "High"
                basic_analysis["recommendation"] = "Immediate clinical consultation required due to pregnancy."
                
        # Simulate epidemiological flagging (e.g. tracking local outbreaks)
        # If symptoms match cholera or malaria in known regions
        epi_flags = []
        cholera_keywords = ["severe diarrhea", "vomiting", "leg cramps"]
        if sum(1 for s in symptoms if s.lower() in cholera_keywords) >= 2:
            epi_flags.append("Suspected Cholera (Report to local health authority)")
            basic_analysis["severity"] = "Critical"
            
        return {
            **basic_analysis,
            "clinical_decision_support": {
                "identified_risk_factors": risk_factors,
                "epidemiological_flags": epi_flags,
                "chw_action_plan": "1. Isolate if infectious. 2. Hydrate. 3. Transport to clinic if severity is High/Critical."
            }
        }

health_analyzer = HealthAnalyzer()
