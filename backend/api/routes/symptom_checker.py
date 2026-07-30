"""
Symptom Checker routes — guided triage flow.
POST /symptom-checker/start   — begin a new triage session
POST /symptom-checker/answer  — submit answer to next question
GET  /symptom-checker/result/{session_id} — get final assessment
"""
import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from backend.api.dependencies.auth import get_current_user
from backend.core.gemini_integration import gemini_client
from backend.core.llm_engine import llm_engine
from backend.utils.logger import get_logger

logger = get_logger(__name__)
symptom_checker_router = APIRouter(prefix="/symptom-checker", tags=["Symptom Checker"])

# In-memory session store (replace with Redis/DB for production)
_sessions: Dict[str, Dict] = {}

QUESTIONS_FLOW = [
    {"id": "age", "question": "How old are you?", "type": "number", "placeholder": "e.g. 25"},
    {"id": "gender", "question": "What is your gender?", "type": "choice", "options": ["Male", "Female", "Other"]},
    {"id": "symptoms", "question": "What are your main symptoms? (describe them)", "type": "text", "placeholder": "e.g. headache, fever, body aches"},
    {"id": "duration", "question": "How long have you had these symptoms?", "type": "choice", "options": ["Less than 24 hours", "1-3 days", "4-7 days", "More than a week"]},
    {"id": "severity", "question": "How severe are your symptoms?", "type": "choice", "options": ["Mild - manageable at home", "Moderate - interfering with daily activities", "Severe - I cannot do normal activities", "Emergency - I need help immediately"]},
    {"id": "pregnant", "question": "Are you pregnant (or could you be)?", "type": "choice", "options": ["Yes", "No", "Not applicable"]},
    {"id": "existing_conditions", "question": "Do you have any existing medical conditions?", "type": "text", "placeholder": "e.g. diabetes, hypertension, asthma, or 'None'"},
]


class StartRequest(BaseModel):
    language: str = Field("English", description="Response language")


class AnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: str


def _build_assessment_prompt(answers: Dict) -> str:
    return f"""You are AfriHealth Assistant performing a symptom triage.

Patient information:
- Age: {answers.get('age', 'Unknown')}
- Gender: {answers.get('gender', 'Unknown')}
- Symptoms: {answers.get('symptoms', 'Not provided')}
- Duration: {answers.get('duration', 'Unknown')}
- Severity: {answers.get('severity', 'Unknown')}
- Pregnant: {answers.get('pregnant', 'Unknown')}
- Existing conditions: {answers.get('existing_conditions', 'None')}

Provide a structured triage assessment:
1. **Likely conditions** (2-3 possibilities based on symptoms)
2. **Urgency level**: Emergency / High / Medium / Low
3. **Recommended action** (home care, clinic visit, ER)
4. **First aid / what to do now**
5. **Warning signs** — when to seek immediate help
6. **What NOT to do**

IMPORTANT: State clearly this is NOT a diagnosis. Recommend professional medical consultation."""


@symptom_checker_router.post("/start", summary="Start a new symptom checker session")
async def start_session(request: StartRequest, current_user=Depends(get_current_user)):
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {"answers": {}, "language": request.language, "step": 0}
    first_q = QUESTIONS_FLOW[0]
    return {
        "session_id": session_id,
        "question": first_q["question"],
        "question_id": first_q["id"],
        "type": first_q["type"],
        "options": first_q.get("options"),
        "placeholder": first_q.get("placeholder"),
        "step": 1,
        "total_steps": len(QUESTIONS_FLOW),
        "complete": False,
    }


@symptom_checker_router.post("/answer", summary="Submit answer and get next question or result")
async def submit_answer(request: AnswerRequest, current_user=Depends(get_current_user)):
    session = _sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    session["answers"][request.question_id] = request.answer
    session["step"] += 1
    step = session["step"]

    if step < len(QUESTIONS_FLOW):
        next_q = QUESTIONS_FLOW[step]
        return {
            "session_id": request.session_id,
            "question": next_q["question"],
            "question_id": next_q["id"],
            "type": next_q["type"],
            "options": next_q.get("options"),
            "placeholder": next_q.get("placeholder"),
            "step": step + 1,
            "total_steps": len(QUESTIONS_FLOW),
            "complete": False,
        }
    else:
        return {"session_id": request.session_id, "complete": True, "step": step, "total_steps": len(QUESTIONS_FLOW)}


@symptom_checker_router.get("/result/{session_id}", summary="Get the triage assessment for a completed session")
async def get_result(session_id: str, current_user=Depends(get_current_user)):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    prompt = _build_assessment_prompt(session["answers"])
    try:
        if gemini_client.is_configured:
            assessment = gemini_client.generate(prompt)
        else:
            assessment = llm_engine.generate(prompt)
    except Exception as exc:
        logger.exception("Assessment generation failed")
        assessment = "Assessment generation failed. Please consult a healthcare professional."

    return {
        "session_id": session_id,
        "assessment": assessment,
        "answers": session["answers"],
        "disclaimer": "This triage is for informational purposes only and does not replace a professional medical diagnosis.",
    }
