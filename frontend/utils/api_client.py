"""
API client for AfriHealth Assistant frontend.

This is the ONE seam where frontend talks to "the backend". Right now
config.BACKEND_CONNECTED is False, so every function below falls back to
local SQLite (db.py) and stub generators. Once the FastAPI backend exists
(routes per the project spec: /chat, /chat/stream, /metrics, /documents/*,
/chat/history), each function here gets a `requests` call instead of a
local fallback - nothing in the pages/components layer needs to change.
"""

import time
import requests
import config
import db
import streamlit as st

def get_auth_headers():
    token = st.session_state.get("access_token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

def login(username, password):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.post(
                f"{config.BACKEND_BASE_URL}/auth/login",
                data={"username": username, "password": password},
                timeout=10,
            )
            return resp.json()
        except requests.RequestException as e:
            return {"detail": f"Connection error: {e}"}
    # Local fallback stub
    return {"access_token": "stub_token", "token_type": "bearer"}

def register(username, password):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.post(
                f"{config.BACKEND_BASE_URL}/auth/register",
                json={"username": username, "password": password},
                timeout=10,
            )
            return resp.json()
        except requests.RequestException as e:
            return {"detail": f"Connection error: {e}"}
    # Local fallback stub
    return {"access_token": "stub_token", "token_type": "bearer"}


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
def stream_chat(query: str, language: str, hybrid: bool = True):
    """Yields response chunks. Maps to POST /chat/stream once backend is live."""
    if config.BACKEND_CONNECTED:
        try:
            with requests.post(
                f"{config.BACKEND_BASE_URL}/chat/stream",
                json={"query": query, "language": language, "hybrid": hybrid},
                headers=get_auth_headers(),
                stream=True,
                timeout=30,
            ) as resp:
                for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
                    if chunk:
                        yield chunk
            return
        except requests.RequestException as e:
            yield f"(Backend unreachable: {e}) "
            return

    # ---- Local stub fallback ----
    lang_note = "" if language == "English" else f" [responding in {language} once backend supports it]"
    full_text = (
        f"(Demo response — backend not connected yet){lang_note}\n\n"
        f"You asked: \"{query}\". Once the RAG + LLM backend is live, "
        f"this will return an evidence-based answer with cited sources, "
        f"streamed word by word from llama.cpp."
    )
    words = full_text.split(" ")
    for i, word in enumerate(words):
        time.sleep(0.02)
        yield word + (" " if i < len(words) - 1 else "")


def get_response_source_stub():
    return "Demo mode — no knowledge base queried"


# ---------------------------------------------------------------------------
# Chat history  (maps to /chat/history GET, /chat/history/{id} DELETE)
# ---------------------------------------------------------------------------
def save_session(messages, session_id=None):
    if config.BACKEND_CONNECTED:
        try:
            payload = {"messages": messages}
            if session_id:
                payload["session_id"] = session_id
            resp = requests.post(
                f"{config.BACKEND_BASE_URL}/chat/history", json=payload, headers=get_auth_headers(), timeout=10
            )
            return resp.json().get("message", "").replace("Saved session ", "")
        except requests.RequestException:
            pass
    return db.save_session(messages, session_id)


def list_sessions(limit=20):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(
                f"{config.BACKEND_BASE_URL}/chat/history", params={"limit": limit}, headers=get_auth_headers(), timeout=10
            )
            return resp.json()
        except requests.RequestException:
            pass
    return db.list_sessions(limit=limit)


def load_session(session_id):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(
                f"{config.BACKEND_BASE_URL}/chat/history/{session_id}", headers=get_auth_headers(), timeout=10
            )
            return resp.json()
        except requests.RequestException:
            pass
    return db.load_session(session_id)


def delete_session(session_id):
    if config.BACKEND_CONNECTED:
        try:
            requests.delete(f"{config.BACKEND_BASE_URL}/chat/history/{session_id}", headers=get_auth_headers(), timeout=10)
            return
        except requests.RequestException:
            pass
    db.delete_session(session_id)


# ---------------------------------------------------------------------------
# Health metrics  (maps to /metrics GET/POST, /metrics/export GET)
# ---------------------------------------------------------------------------
def add_health_metric(metric_type: str, value: str, unit: str = "", notes: str = "", patient_id: int = None):
    payload = {
        "metric_type": metric_type,
        "value": value,
        "unit": unit,
        "notes": notes,
        "patient_id": patient_id
    }
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.post(f"{config.BACKEND_BASE_URL}/metrics", json=payload, headers=get_auth_headers(), timeout=5)
            return resp.json()
        except requests.RequestException:
            pass
    return db.db_manager.add_health_entry(
        user_id=st.session_state.get("user_id", 1),
        patient_id=patient_id,
        metric_type=metric_type,
        value=value,
        unit=unit,
        notes=notes
    )


def get_health_metrics(metric_type: str = None, limit: int = 200, patient_id: int = None):
    if config.BACKEND_CONNECTED:
        try:
            params = {"limit": limit}
            if metric_type: params["metric_type"] = metric_type
            if patient_id: params["patient_id"] = patient_id
            resp = requests.get(f"{config.BACKEND_BASE_URL}/metrics", params=params, headers=get_auth_headers(), timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("metrics", [])
            return []
        except requests.RequestException:
            pass
    return db.db_manager.get_health_entries(
        limit=limit,
        user_id=st.session_state.get("user_id", 1),
        patient_id=patient_id
    )


def delete_health_entry(entry_id):
    if config.BACKEND_CONNECTED:
        try:
            requests.delete(f"{config.BACKEND_BASE_URL}/metrics/{entry_id}", headers=get_auth_headers(), timeout=10)
            return
        except requests.RequestException:
            pass
    db.delete_health_entry(entry_id)


def request_personalized_coach(metrics, patient_context=None):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.post(
                f"{config.BACKEND_BASE_URL}/clinical/cds",
                json={"symptoms": metrics, "patient_context": patient_context},
                headers=get_auth_headers(),
                timeout=20,
            )
            return resp.json()
        except requests.RequestException as e:
            return {"error": f"Coach request failed: {e}"}
    return {
        "insights": ["Demo coach recommendations will appear once backend is connected."],
        "risk_alerts": [],
        "recommendations": ["Track your metrics and consult a health worker regularly."],
        "follow_up": ["Follow up weekly on your health metrics."],
    }


def request_clinical_triage(symptoms, patient_context=None):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.post(
                f"{config.BACKEND_BASE_URL}/clinical/triage",
                json={"symptoms": symptoms, "patient_context": patient_context},
                headers=get_auth_headers(),
                timeout=20,
            )
            return resp.json()
        except requests.RequestException as e:
            return {"error": f"Clinical triage failed: {e}"}
    return {
        "urgency": "Low",
        "advice": "Demo clinical triage will appear once backend is connected.",
        "do_not": [],
        "identified_risk_factors": [],
        "epidemiological_flags": [],
        "chw_action_plan": "Monitor and consult a clinician if symptoms worsen.",
    }


def request_medication_interactions(medications):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.post(
                f"{config.BACKEND_BASE_URL}/clinical/drugs/interact",
                json={"drugs": medications},
                headers=get_auth_headers(),
                timeout=20,
            )
            return resp.json()
        except requests.RequestException as e:
            return {"error": f"Medication interaction check failed: {e}"}
    return {
        "interactions": [],
        "safe_to_continue": True,
        "notes": ["Demo medication interaction checking will appear once backend is connected."],
    }


def request_treatment_protocol(condition):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(
                f"{config.BACKEND_BASE_URL}/clinical/protocols",
                params={"condition": condition},
                headers=get_auth_headers(),
                timeout=20,
            )
            return resp.json()
        except requests.RequestException as e:
            return {"error": f"Protocol lookup failed: {e}"}
    return {
        "condition": condition,
        "protocol": ["Demo protocol results will appear once backend is connected."],
        "references": ["Offline protocol support is not yet connected."],
    }


# ---------------------------------------------------------------------------
# Documents  (maps to /documents/upload, /documents/analyze)
# ---------------------------------------------------------------------------
def upload_document(file_obj, filename: str, patient_id: int = None):
    if config.BACKEND_CONNECTED:
        try:
            files = {"file": (filename, file_obj)}
            data = {"patient_id": patient_id} if patient_id else {}
            resp = requests.post(f"{config.BACKEND_BASE_URL}/documents/upload", files=files, data=data, headers=get_auth_headers(), timeout=30)
            return resp.json()
        except requests.RequestException as e:
            return {"status": "error", "message": f"Upload failed: {str(e)}"}
    return {"status": "error", "message": "Backend disconnected."}

def analyze_document(filename: str):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.post(
                f"{config.BACKEND_BASE_URL}/documents/analyze",
                json={"filename": filename},
                headers=get_auth_headers(),
                timeout=20,
            )
            return resp.json()
        except requests.RequestException as e:
            return {"detail": f"Analyze error: {e}"}
    return analyze_document_stub(filename)

def get_documents(limit: int = 50, patient_id: int = None):
    if config.BACKEND_CONNECTED:
        try:
            params = {"limit": limit}
            if patient_id: params["patient_id"] = patient_id
            resp = requests.get(f"{config.BACKEND_BASE_URL}/documents", params=params, headers=get_auth_headers(), timeout=5)
            if resp.status_code == 200:
                return resp.json()
            return []
        except requests.RequestException:
            pass
    return db.db_manager.get_documents(limit=limit, user_id=st.session_state.get("user_id", 1), patient_id=patient_id)

def analyze_document_stub(filename: str):
    """Placeholder for OCR + RAG interpretation until backend is connected."""
    time.sleep(0.8)
    return {
        "status": "success",
        "extracted_text_preview": "(Demo) OCR extraction will appear here once easyOCR is connected.",
        "analysis": (
            f"(Demo) AI interpretation of '{filename}' will appear here once the "
            "RAG pipeline is connected to /documents/analyze."
        ),
        "source": "Demo mode",
    }


# ---------------------------------------------------------------------------
# System status  (maps to /health, /status, /online/status)
# ---------------------------------------------------------------------------
def get_system_status():
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(f"{config.BACKEND_BASE_URL}/system/status", timeout=5)
            return resp.json()
        except requests.RequestException:
            return {"model_loaded": False, "memory_usage_gb": None, "online": False}
    return {"model_loaded": True, "memory_usage_gb": 4.2, "online": False}

def get_online_status():
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(f"{config.BACKEND_BASE_URL}/online/status", timeout=5)
            return resp.json()
        except requests.RequestException:
            pass
    # Local fallback for hybrid mode
    import requests as req
    try:
        req.get("https://duckduckgo.com", timeout=2)
        return {"status": "online", "hybrid_mode_active": True, "search_engine": "DuckDuckGo"}
    except:
        return {"status": "offline", "hybrid_mode_active": False, "search_engine": None}

def perform_online_search(query: str, limit: int = 5):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.post(f"{config.BACKEND_BASE_URL}/online/search", json={"query": query, "limit": limit}, headers=get_auth_headers(), timeout=10)
            return resp.json()
        except requests.RequestException:
            pass
    return {"results": [], "error": "Backend disconnected."}


# ---------------------------------------------------------------------------
# Patient Management
# ---------------------------------------------------------------------------
def get_patients(search: str = None):
    if config.BACKEND_CONNECTED:
        try:
            params = {"search": search} if search else {}
            resp = requests.get(
                f"{config.BACKEND_BASE_URL}/patients",
                params=params,
                headers=get_auth_headers(),
                timeout=10
            )
            return resp.json()
        except requests.RequestException as e:
            st.error(f"Failed to fetch patients: {e}")
            return []
    # Local fallback
    return db.db_manager.get_patients(search=search)

def create_patient(payload: dict):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.post(
                f"{config.BACKEND_BASE_URL}/patients",
                json=payload,
                headers=get_auth_headers(),
                timeout=10
            )
            return resp.json()
        except requests.RequestException as e:
            return {"success": False, "detail": str(e)}
    # Local fallback
    try:
        patient_id = db.db_manager.create_patient(payload)
        return {"success": True, "patient_id": patient_id}
    except Exception as e:
        return {"success": False, "detail": str(e)}

def get_patient(patient_id: int):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(
                f"{config.BACKEND_BASE_URL}/patients/{patient_id}",
                headers=get_auth_headers(),
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json()
            return None
        except requests.RequestException:
            return None
    # Local fallback
    return db.db_manager.get_patient(patient_id)

def get_patient_visits(patient_id: int):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(
                f"{config.BACKEND_BASE_URL}/patients/{patient_id}/visits",
                headers=get_auth_headers(),
                timeout=10
            )
            return resp.json()
        except requests.RequestException:
            return []
    # Local fallback
    return db.db_manager.get_patient_visits(patient_id)

def create_visit(patient_id: int, payload: dict):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.post(
                f"{config.BACKEND_BASE_URL}/patients/{patient_id}/visits",
                json=payload,
                headers=get_auth_headers(),
                timeout=30 # May take time for AI diagnosis
            )
            return resp.json()
        except requests.RequestException as e:
            return {"success": False, "detail": str(e)}
    # Local fallback
    # Auto-generate some dummy AI suggestions if offline and no real model attached
    if not payload.get("ai_suggestions"):
        payload["ai_suggestions"] = "(Offline Fallback) AI suggests rest and hydration based on symptoms."
    try:
        payload["patient_id"] = patient_id
        visit_id = db.db_manager.create_visit(payload)
        return {"success": True, "visit_id": visit_id}
    except Exception as e:
        return {"success": False, "detail": str(e)}
