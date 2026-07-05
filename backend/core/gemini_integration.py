import json
import logging
from typing import Dict, Any, List, Optional
import google.generativeai as genai

from backend.config import settings

logger = logging.getLogger(__name__)

class GeminiIntegration:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.is_configured = bool(self.api_key)
        self.model_name = "gemini-3.1-pro"
        
        if self.is_configured:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            logger.warning("Gemini API key not configured. Cloud fallback disabled.")
            self.model = None

    def get_status(self) -> Dict[str, Any]:
        """Returns the connection status of Gemini API"""
        if not self.is_configured:
            return {"status": "offline", "configured": False}
        
        try:
            # Simple ping to verify connection
            _ = self.model.generate_content("ping")
            return {"status": "online", "configured": True, "model": self.model_name}
        except Exception as e:
            logger.error(f"Gemini API connection error: {e}")
            return {"status": "error", "configured": True, "error": str(e)}

    def generate(self, prompt: str, system_instruction: str = None) -> str:
        if not self.is_configured:
            raise ValueError("Gemini API not configured")
            
        try:
            model = self.model
            if system_instruction:
                # system_instruction is supported natively in modern SDK but passing via content for compatibility
                model = genai.GenerativeModel(self.model_name, system_instruction=system_instruction)
            
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini generate error: {e}")
            raise e

    def stream_generate(self, prompt: str, system_instruction: str = None):
        if not self.is_configured:
            raise ValueError("Gemini API not configured")
            
        try:
            model = self.model
            if system_instruction:
                model = genai.GenerativeModel(self.model_name, system_instruction=system_instruction)
            
            response = model.generate_content(prompt, stream=True)
            for chunk in response:
                yield chunk.text
        except Exception as e:
            logger.error(f"Gemini stream_generate error: {e}")
            raise e

    def analyze_document(self, text: str, context: str = "") -> str:
        prompt = f"Analyze the following medical document and extract key findings. Context: {context}\n\nDocument:\n{text}"
        return self.generate(prompt)

    def check_drug_interaction(self, drugs: List[str]) -> Dict[str, Any]:
        prompt = f"""
        Act as a clinical pharmacologist. Check for drug interactions among the following medications: {', '.join(drugs)}.
        Return a JSON response with the following format:
        {{
            "interactions": ["list of potential interactions"],
            "notes": ["additional clinical notes or warnings"],
            "severity": "high/medium/low/none"
        }}
        Ensure the response is valid JSON only.
        """
        response = self.generate(prompt)
        try:
            # Clean up the response in case there are markdown code blocks
            text = response.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse Gemini drug interaction response as JSON: {response}")
            return {"interactions": ["Failed to parse interactions from AI."], "notes": [], "severity": "unknown"}

    def clinical_decision_support(self, symptoms: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
        Act as an expert clinical decision support system.
        Patient Context: {json.dumps(context)}
        Reported Symptoms: {', '.join(symptoms)}
        
        Provide clinical recommendations, possible differential diagnoses, and risk factors.
        Return a JSON response strictly in the following format:
        {{
            "possible_conditions": ["Condition A", "Condition B"],
            "recommendations": ["Recommendation 1", "Recommendation 2"],
            "risk_factors": ["Risk 1"],
            "urgency": "high/medium/low"
        }}
        """
        response = self.generate(prompt)
        try:
            text = response.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except json.JSONDecodeError:
            return {"possible_conditions": [], "recommendations": ["Error analyzing symptoms"], "risk_factors": [], "urgency": "unknown"}

    def generate_triage(self, symptoms: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
        Act as an emergency triage nurse.
        Patient Context: {json.dumps(context)}
        Symptoms: {', '.join(symptoms)}
        
        Assess the urgency and provide immediate advice.
        Return a JSON response strictly in the following format:
        {{
            "urgency": "Critical/Emergency/High/Medium/Low",
            "advice": "Immediate advice for the patient",
            "do_not": ["Things patient should avoid doing"],
            "identified_risk_factors": ["Risk A"],
            "epidemiological_flags": ["Flag A"]
        }}
        """
        response = self.generate(prompt)
        try:
            text = response.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except json.JSONDecodeError:
            return {"urgency": "Unknown", "advice": "Please consult a healthcare professional immediately.", "do_not": [], "identified_risk_factors": [], "epidemiological_flags": []}

    def check_cost(self) -> Dict[str, Any]:
        """Mock method for cost tracking"""
        return {
            "estimated_cost_usd": 0.05,
            "tokens_used": 1500,
            "monthly_limit": 10.00
        }

gemini_client = GeminiIntegration()
