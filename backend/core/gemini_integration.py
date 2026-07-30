"""
Gemini Cloud Integration — uses google-genai SDK (v1+).
Provides generate() and stream_generate() using Gemini models
as a cloud fallback when the local LLM is unavailable.
"""
import json
import logging
from typing import Dict, Any, List, Generator, Optional

from backend.config import settings
from backend.utils.metrics import track_api_cost

logger = logging.getLogger(__name__)

_GENAI_AVAILABLE = False
try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except ImportError:
    logger.warning("google-genai not installed. Cloud fallback disabled.")


class GeminiIntegration:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.is_configured = bool(self.api_key) and _GENAI_AVAILABLE
        self.model_name = "gemini-2.0-flash"   # fast + widely available
        self._client = None
        self._total_tokens = 0
        self._total_cost = 0.0

        if self.is_configured:
            try:
                self._client = genai.Client(api_key=self.api_key)
                logger.info("Gemini cloud fallback ready (model=%s).", self.model_name)
            except Exception as exc:
                logger.error("Failed to create Gemini client: %s", exc)
                self.is_configured = False
        else:
            logger.warning("Gemini API key not configured or google-genai not installed. Cloud fallback disabled.")

    # ------------------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        if not self.is_configured:
            return {"status": "offline", "configured": False}
        try:
            resp = self._client.models.generate_content(
                model=self.model_name,
                contents="ping"
            )
            return {"status": "online", "configured": True, "model": self.model_name}
        except Exception as exc:
            logger.error("Gemini API connection error: %s", exc)
            return {"status": "error", "configured": True, "error": str(exc)}

    # ------------------------------------------------------------------
    def generate(self, prompt: str, system_instruction: str = None) -> str:
        if not self.is_configured:
            raise ValueError("Gemini API not configured")
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction or (
                    "You are AfriHealth Assistant, an expert medical AI for African healthcare contexts."
                ),
                temperature=0.7,
                max_output_tokens=1024,
            )
            # Try models in priority order
            for model in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.0-pro"]:
                try:
                    response = self._client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=config,
                    )
                    self.model_name = model  # update to the working model
                    text = response.text or ""
                    tokens = max(1, len(text.split()))
                    self._total_tokens += tokens
                    self._total_cost += tokens * 0.000001
                    track_api_cost(tokens * 0.000001, tokens)
                    return text
                except Exception as exc:
                    last_exc = exc
                    logger.warning("Model %s failed: %s — trying next...", model, exc)
            raise last_exc
        except Exception as exc:
            logger.error("Gemini generate error: %s", exc)
            raise exc

    # ------------------------------------------------------------------
    def stream_generate(self, prompt: str, system_instruction: str = None) -> Generator[str, None, None]:
        if not self.is_configured:
            raise ValueError("Gemini API not configured")
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction or (
                    "You are AfriHealth Assistant, an expert medical AI for African healthcare contexts."
                ),
                temperature=0.7,
                max_output_tokens=1024,
            )
            for chunk in self._client.models.generate_content_stream(
                model=self.model_name,
                contents=prompt,
                config=config,
            ):
                if chunk.text:
                    yield chunk.text
        except Exception as exc:
            logger.error("Gemini stream_generate error: %s", exc)
            raise exc

    # ------------------------------------------------------------------
    def analyze_document(self, text: str, context: str = "") -> str:
        prompt = (
            f"Analyze the following medical document and extract key findings.\n"
            f"Context: {context}\n\nDocument:\n{text}"
        )
        return self.generate(prompt)

    def transcribe_audio(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        """Transcribe a short voice question through the configured cloud model."""
        if not self.is_configured:
            raise ValueError("Audio transcription requires a configured cloud provider")
        prompt = (
            "Transcribe this recording exactly as spoken. Return only the transcript, "
            "with no commentary. The recording may contain a health question."
        )
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=[types.Part.from_bytes(data=audio_bytes, mime_type=mime_type), prompt],
        )
        text = (response.text or "").strip()
        if not text:
            raise ValueError("The audio recording did not contain recognizable speech")
        return text

    def check_drug_interaction(self, drugs: List[str]) -> Dict[str, Any]:
        prompt = f"""Act as a clinical pharmacologist. Check for drug interactions among: {', '.join(drugs)}.
Return JSON only:
{{
    "interactions": ["list of potential interactions"],
    "notes": ["additional clinical notes"],
    "severity": "high/medium/low/none"
}}"""
        response = self.generate(prompt)
        try:
            text = response.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except json.JSONDecodeError:
            return {"interactions": ["Failed to parse interactions."], "notes": [], "severity": "unknown"}

    def clinical_decision_support(self, symptoms: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""Act as an expert clinical decision support system.
Patient Context: {json.dumps(context)}
Reported Symptoms: {', '.join(symptoms)}

Return JSON only:
{{
    "possible_conditions": ["Condition A"],
    "recommendations": ["Recommendation 1"],
    "risk_factors": ["Risk 1"],
    "urgency": "high/medium/low"
}}"""
        response = self.generate(prompt)
        try:
            text = response.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except json.JSONDecodeError:
            return {"possible_conditions": [], "recommendations": ["Error analyzing symptoms"], "risk_factors": [], "urgency": "unknown"}

    def generate_triage(self, symptoms: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""Act as an emergency triage nurse.
Patient Context: {json.dumps(context)}
Symptoms: {', '.join(symptoms)}

Return JSON only:
{{
    "urgency": "Critical/Emergency/High/Medium/Low",
    "advice": "Immediate advice",
    "do_not": ["Things to avoid"],
    "identified_risk_factors": ["Risk A"],
    "epidemiological_flags": ["Flag A"]
}}"""
        response = self.generate(prompt)
        try:
            text = response.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except json.JSONDecodeError:
            return {"urgency": "Unknown", "advice": "Consult a healthcare professional immediately.", "do_not": [], "identified_risk_factors": [], "epidemiological_flags": []}

    def check_cost(self) -> Dict[str, Any]:
        return {"estimated_cost_usd": round(self._total_cost, 6), "tokens_used": self._total_tokens, "monthly_limit": 10.00}


gemini_client = GeminiIntegration()
