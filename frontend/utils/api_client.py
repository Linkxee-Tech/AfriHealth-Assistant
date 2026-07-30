"""
API client for AfriHealth Assistant frontend.

This is the ONE seam where the frontend talks to the backend. The connection
URL and enabled/disabled state come from the project `.env`; when disabled,
chat/history/metrics use the local SQLite fallback and backend-only features
return safe unavailable responses.
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
                timeout=2,
            )
            return resp.json()
        except requests.RequestException as e:
            return {"detail": f"Connection error: {e}"}
    return {
        "detail": (
            "Backend disconnected; login requires the FastAPI authentication service."
        )
    }

def register(username, password, email=""):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.post(
                f"{config.BACKEND_BASE_URL}/auth/register",
                json={"username": username, "password": password, "email": email or None},
                timeout=10,
            )
            return resp.json()
        except requests.RequestException as e:
            return {"detail": f"Connection error: {e}"}
    return {
        "detail": (
            "Backend disconnected; registration requires the FastAPI authentication service."
        )
    }


def request_password_reset(username: str = "", email: str = ""):
    if config.BACKEND_CONNECTED:
        try:
            payload = {key: value for key, value in {"username": username.strip(), "email": email.strip()}.items() if value}
            resp = requests.post(f"{config.BACKEND_BASE_URL}/auth/forgot-password", json=payload, timeout=15)
            return resp.json()
        except requests.RequestException as exc:
            return {"success": False, "detail": str(exc)}
    return {"success": False, "detail": "Backend disconnected; password recovery is unavailable."}


def reset_password(token: str, new_password: str):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.post(f"{config.BACKEND_BASE_URL}/auth/reset-password", json={"token": token, "new_password": new_password}, timeout=15)
            return resp.json()
        except requests.RequestException as exc:
            return {"success": False, "detail": str(exc)}
    return {"success": False, "detail": "Backend disconnected; password recovery is unavailable."}


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
def stream_chat(query: str, language: str, hybrid: bool = True, detail_level: str = "Standard"):
    """Yields response chunks including __SOURCES__ header. Maps to POST /chat/stream."""
    if config.BACKEND_CONNECTED:
        try:
            with requests.post(
                f"{config.BACKEND_BASE_URL}/chat/stream",
                json={"query": query, "language": language, "hybrid": hybrid},
                headers=get_auth_headers(),
                stream=True,
                timeout=30,
            ) as resp:
                buffer = ""
                for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
                    if not chunk:
                        continue
                    buffer += chunk
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        # Pass __SOURCES__ through to the chat page so it can display them
                        yield line + "\n"
                if buffer:
                    yield buffer
            return
        except requests.RequestException as e:
            yield f"(Backend unreachable: {e}) "
            return

    # ---- Explicit disconnected-backend fallback ----
    lang_note = "" if language == "English" else f" Requested language: {language}."
    full_text = (
        "No AI answer was generated because the FastAPI backend is not connected. "
        "Start the backend and confirm BACKEND_CONNECTED=True before using clinical chat."
        f"{lang_note}\n\nYour question was received: \"{query}\"."
    )
    words = full_text.split(" ")
    for i, word in enumerate(words):
        time.sleep(0.02)
        yield word + (" " if i < len(words) - 1 else "")


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


def _normalise_session(session):
    """Expose one history shape to pages regardless of the storage backend."""
    return {
        **session,
        "session_id": session.get("session_id", session.get("id", "")),
        "preview": session.get("preview", session.get("topic", "")),
        "created_at": session.get("created_at", session.get("started_at", "")),
    }


def list_sessions(limit=20):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(
                f"{config.BACKEND_BASE_URL}/chat/history", params={"limit": limit}, headers=get_auth_headers(), timeout=10
            )
            sessions = resp.json() if resp.status_code == 200 else []
            # Keep the frontend contract compatible with the local SQLite
            # fallback while the backend uses topic/started_at names.
            if isinstance(sessions, list):
                return [_normalise_session(session) for session in sessions if isinstance(session, dict)]
        except requests.RequestException:
            pass
    return [_normalise_session(session) for session in db.list_sessions(limit=limit)]


def load_session(session_id):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(
                f"{config.BACKEND_BASE_URL}/chat/history/{session_id}", headers=get_auth_headers(), timeout=10
            )
            data = resp.json() if resp.status_code == 200 else []
            return data if isinstance(data, list) else []
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
def add_health_metric(metric_type: str, value: str, unit: str = "", notes: str = "", patient_id: int = None, recorded_at=None):
    payload = {
        "metric_type": metric_type,
        "value": value,
        "unit": unit,
        "notes": notes,
        "patient_id": patient_id,
        "recorded_at": recorded_at.isoformat() if recorded_at else None,
    }
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.post(f"{config.BACKEND_BASE_URL}/metrics", json=payload, headers=get_auth_headers(), timeout=5)
            return resp.json()
        except requests.RequestException:
            pass
    return db.add_health_entry(metric_type, value, unit, notes, recorded_at=recorded_at)


def check_vitals(metric_type: str, value: str):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.post(
                f"{config.BACKEND_BASE_URL}/metrics/check-vitals",
                json={"metric_type": metric_type, "value": value},
                headers=get_auth_headers(),
                timeout=10,
            )
            return resp.json()
        except requests.RequestException:
            pass
    return {"status": "unknown", "urgency": "Low", "message": "Backend unavailable for vital analysis."}


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
    return db.get_health_entries(metric_type=metric_type, limit=limit)


def add_health_entry(metric_type: str, value: str, unit: str = "", notes: str = None, patient_id: int = None, recorded_at=None):
    """Compatibility name used by the reusable metrics component."""
    return add_health_metric(metric_type, value, unit, notes or "", patient_id, recorded_at)


def get_health_entries(metric_type: str = None, limit: int = 200, patient_id: int = None):
    """Return health entries using the component's legacy logged_at field too."""
    entries = get_health_metrics(metric_type=metric_type, limit=limit, patient_id=patient_id)
    for entry in entries:
        entry.setdefault("logged_at", entry.get("recorded_at", ""))
    return entries


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
                f"{config.BACKEND_BASE_URL}/metrics/coach",
                json={"metrics": metrics, "patient_context": patient_context},
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
        for attempt in range(10):
            try:
                resp = requests.post(
                    f"{config.BACKEND_BASE_URL}/documents/analyze",
                    json={"filename": filename},
                    headers=get_auth_headers(),
                    timeout=20,
                )
                if resp.status_code == 404 and attempt < 9:
                    time.sleep(0.5)
                    continue
                return resp.json()
            except requests.RequestException as e:
                return {"detail": f"Analyze error: {e}"}
    return analyze_document_stub(filename)


def transcribe_audio(audio_bytes: bytes, content_type: str = "audio/wav") -> dict:
    """Transcribe audio using the backend /voice/transcribe (offline Whisper)."""
    if config.BACKEND_CONNECTED:
        try:
            import io
            ext_map = {"audio/wav": "wav", "audio/webm": "webm", "audio/ogg": "ogg", "audio/mp3": "mp3", "audio/mpeg": "mp3"}
            ext = ext_map.get(content_type, "wav")
            files = {"audio": (f"recording.{ext}", io.BytesIO(audio_bytes), content_type)}
            resp = requests.post(
                f"{config.BACKEND_BASE_URL}/voice/transcribe",
                files=files,
                headers=get_auth_headers(),
                timeout=60,
            )
            return resp.json()
        except requests.RequestException as exc:
            return {"text": "", "detail": f"Voice request failed: {exc}"}
    return {"text": "", "detail": "Backend disconnected; voice transcription is unavailable."}

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
    return []

def analyze_document_stub(filename: str):
    """Return an explicit unavailable result when the backend is disconnected."""
    return {
        "status": "unavailable",
        "detail": (
            "Document analysis is unavailable because the FastAPI backend is not connected. "
            f"No OCR or clinical interpretation was generated for '{filename}'."
        ),
    }


# ---------------------------------------------------------------------------
# System status  (maps to /health, /status, /online/status)
# ---------------------------------------------------------------------------
def get_system_status():
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(f"{config.BACKEND_BASE_URL}/status", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                st.session_state["model_loaded"] = bool(data.get("model_loaded"))
                st.session_state["memory_usage_gb"] = data.get("memory_usage_gb") or 0.0
                st.session_state["gemini_configured"] = bool(data.get("gemini_configured"))
                return data
            return {"model_loaded": False, "memory_usage_gb": None, "online": False, "error": resp.text}
        except requests.RequestException:
            return {"model_loaded": False, "memory_usage_gb": None, "online": False}
    return {"model_loaded": False, "memory_usage_gb": None, "online": False, "error": "Backend disconnected."}

def get_online_status():
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(f"{config.BACKEND_BASE_URL}/online/status", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                st.session_state["processing_mode"] = "HYBRID" if data.get("hybrid_mode_active") else "OFFLINE"
                return data
        except requests.RequestException:
            pass
    # Local fallback for hybrid mode
    import requests as req
    try:
        req.get("https://duckduckgo.com", timeout=2)
        return {"status": "online", "hybrid_mode_active": True, "search_engine": "DuckDuckGo"}
    except:
        return {"status": "offline", "hybrid_mode_active": False, "search_engine": None}


def get_online_cost():
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(f"{config.BACKEND_BASE_URL}/online/cost", headers=get_auth_headers(), timeout=10)
            return resp.json() if resp.status_code == 200 else {"error": resp.text}
        except requests.RequestException as exc:
            return {"error": str(exc)}
    return {"error": "Backend disconnected."}

def perform_online_search(query: str, limit: int = 5):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.post(f"{config.BACKEND_BASE_URL}/online/search", json={"query": query, "limit": limit}, headers=get_auth_headers(), timeout=10)
            return resp.json()
        except requests.RequestException:
            pass
    return {"results": [], "error": "Backend disconnected."}


def get_settings():
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(
                f"{config.BACKEND_BASE_URL}/settings",
                headers=get_auth_headers(),
                timeout=2,
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": resp.text}
        except requests.RequestException as exc:
            return {"error": str(exc)}
    return {"error": "Backend disconnected."}


def update_settings(values: dict):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.put(
                f"{config.BACKEND_BASE_URL}/settings",
                json=values,
                headers=get_auth_headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": resp.text}
        except requests.RequestException as exc:
            return {"error": str(exc)}
    return {"error": "Backend disconnected."}


def sync_data():
    if not config.BACKEND_CONNECTED:
        return {"success": False, "message": "Backend disconnected."}
    try:
        resp = requests.post(
            f"{config.BACKEND_BASE_URL}/online/sync",
            headers=get_auth_headers(),
            timeout=15,
        )
        data = resp.json()
        if resp.status_code >= 400:
            data.setdefault("success", False)
        return data
    except requests.RequestException as exc:
        return {"success": False, "message": str(exc)}


def download_backup():
    if not config.BACKEND_CONNECTED:
        return None, "Backend disconnected."
    try:
        resp = requests.get(
            f"{config.BACKEND_BASE_URL}/online/backup",
            headers=get_auth_headers(),
            timeout=30,
        )
        if resp.status_code != 200:
            return None, resp.text
        return resp.content, resp.headers.get("Content-Disposition", "afrihealth-backup.json")
    except requests.RequestException as exc:
        return None, str(exc)


def clear_chat_history():
    if not config.BACKEND_CONNECTED:
        return {"success": False, "message": "Backend disconnected."}
    try:
        resp = requests.delete(
            f"{config.BACKEND_BASE_URL}/chat/history",
            headers=get_auth_headers(),
            timeout=15,
        )
        return resp.json()
    except requests.RequestException as exc:
        return {"success": False, "message": str(exc)}


def clear_health_metrics():
    if not config.BACKEND_CONNECTED:
        return {"success": False, "message": "Backend disconnected."}
    try:
        resp = requests.delete(
            f"{config.BACKEND_BASE_URL}/metrics",
            headers=get_auth_headers(),
            timeout=15,
        )
        return resp.json()
    except requests.RequestException as exc:
        return {"success": False, "message": str(exc)}


def reset_settings():
    if not config.BACKEND_CONNECTED:
        return {"error": "Backend disconnected."}
    try:
        resp = requests.post(
            f"{config.BACKEND_BASE_URL}/settings/reset",
            headers=get_auth_headers(),
            timeout=15,
        )
        return resp.json()
    except requests.RequestException as exc:
        return {"error": str(exc)}


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
            data = resp.json() if resp.status_code == 200 else []
            return data if isinstance(data, list) else []
        except requests.RequestException as e:
            st.error(f"Failed to fetch patients: {e}")
            return []
    # Patient records require the backend database; fail safely when it is unavailable.
    return []

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
    return {"success": False, "detail": "Patient service unavailable while backend is disconnected."}

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
    return None

def export_patient(patient_id: int):
    """Return a serialisable patient record and visit history for download."""
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(
                f"{config.BACKEND_BASE_URL}/patients/{patient_id}/export",
                headers=get_auth_headers(),
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException:
            pass
    return {"patient": {}, "visits": []}


def download_patient_pdf(patient_id: int):
    if not config.BACKEND_CONNECTED:
        return None, "Backend disconnected."
    try:
        resp = requests.get(
            f"{config.BACKEND_BASE_URL}/patients/{patient_id}/export/pdf",
            headers=get_auth_headers(),
            timeout=30,
        )
        if resp.status_code != 200:
            return None, resp.text
        return resp.content, resp.headers.get("Content-Disposition", "patient-report.pdf")
    except requests.RequestException as exc:
        return None, str(exc)

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
    return []

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
    return {"success": False, "detail": "Visit service unavailable while backend is disconnected."}


def update_patient(patient_id: int, payload: dict):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.put(
                f"{config.BACKEND_BASE_URL}/patients/{patient_id}",
                json=payload,
                headers=get_auth_headers(),
                timeout=10,
            )
            return resp.json()
        except requests.RequestException as e:
            return {"success": False, "detail": str(e)}
    return {"success": False, "detail": "Patient service unavailable while backend is disconnected."}


def delete_patient(patient_id: int):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.delete(
                f"{config.BACKEND_BASE_URL}/patients/{patient_id}",
                headers=get_auth_headers(),
                timeout=10,
            )
            return resp.json()
        except requests.RequestException as e:
            return {"success": False, "detail": str(e)}
    return {"success": False, "detail": "Patient service unavailable while backend is disconnected."}


def download_prescription_pdf(visit_id: int):
    if not config.BACKEND_CONNECTED:
        return None, "Backend disconnected."
    try:
        resp = requests.get(f"{config.BACKEND_BASE_URL}/visits/{visit_id}/prescription/pdf", headers=get_auth_headers(), timeout=30)
        if resp.status_code != 200:
            return None, resp.text
        return resp.content, resp.headers.get("Content-Disposition", f"prescription-{visit_id}.pdf")
    except requests.RequestException as exc:
        return None, str(exc)


def get_guidelines(category=None, query=None):
    if not config.BACKEND_CONNECTED:
        return []
    try:
        params = {key: value for key, value in {"category": category, "query": query}.items() if value}
        resp = requests.get(f"{config.BACKEND_BASE_URL}/clinical/guidelines", params=params, headers=get_auth_headers(), timeout=15)
        return resp.json() if resp.status_code == 200 else []
    except requests.RequestException:
        return []


def download_guideline_pdf(guideline_id: int):
    if not config.BACKEND_CONNECTED:
        return None, "Backend disconnected."
    try:
        resp = requests.get(f"{config.BACKEND_BASE_URL}/clinical/guidelines/{guideline_id}/pdf", headers=get_auth_headers(), timeout=30)
        if resp.status_code != 200:
            return None, resp.text
        return resp.content, resp.headers.get("Content-Disposition", f"guideline-{guideline_id}.pdf")
    except requests.RequestException as exc:
        return None, str(exc)


def search_drugs(query=""):
    if not config.BACKEND_CONNECTED:
        return []
    try:
        resp = requests.get(f"{config.BACKEND_BASE_URL}/clinical/drugs", params={"query": query}, headers=get_auth_headers(), timeout=15)
        return resp.json() if resp.status_code == 200 else []
    except requests.RequestException:
        return []


def calculate_bmi(height_cm, weight_kg):
    if not config.BACKEND_CONNECTED:
        return {"error": "Backend disconnected."}
    try:
        resp = requests.post(f"{config.BACKEND_BASE_URL}/clinical/calculators/bmi", json={"height_cm": height_cm, "weight_kg": weight_kg}, headers=get_auth_headers(), timeout=10)
        return resp.json()
    except requests.RequestException as exc:
        return {"error": str(exc)}


def calculate_egfr(creatinine_mg_dl, age, sex):
    if not config.BACKEND_CONNECTED:
        return {"error": "Backend disconnected."}
    try:
        resp = requests.post(f"{config.BACKEND_BASE_URL}/clinical/calculators/egfr", json={"creatinine_mg_dl": creatinine_mg_dl, "age": age, "sex": sex}, headers=get_auth_headers(), timeout=10)
        return resp.json()
    except requests.RequestException as exc:
        return {"error": str(exc)}


def get_vaccination_schedule(age_years):
    if not config.BACKEND_CONNECTED:
        return {"schedule": [], "error": "Backend disconnected."}
    try:
        resp = requests.get(f"{config.BACKEND_BASE_URL}/clinical/vaccinations", params={"age_years": age_years}, headers=get_auth_headers(), timeout=10)
        return resp.json()
    except requests.RequestException as exc:
        return {"schedule": [], "error": str(exc)}


def get_response_source_stub():
    """Return citations captured from the streaming response header."""
    sources = st.session_state.get("response_sources", [])
    return "; ".join(sources) if sources else "No source citation returned"

def _base_url() -> str:
    return config.BACKEND_BASE_URL

def _auth_headers() -> dict:
    return get_auth_headers()

def _get(endpoint: str, params: dict = None) -> dict:
    try:
        resp = requests.get(
            f"{_base_url()}{endpoint}",
            params=params,
            headers=_auth_headers(),
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"detail": resp.text}
    except Exception as exc:
        return {"detail": str(exc)}

def _post(endpoint: str, payload: dict) -> dict:
    try:
        resp = requests.post(
            f"{_base_url()}{endpoint}",
            json=payload,
            headers=_auth_headers(),
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"detail": resp.text}
    except Exception as exc:
        return {"detail": str(exc)}

def _delete(endpoint: str) -> dict:
    try:
        resp = requests.delete(
            f"{_base_url()}{endpoint}",
            headers=_auth_headers(),
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"detail": resp.text}
    except Exception as exc:
        return {"detail": str(exc)}

def start_symptom_checker(language: str = "English") -> dict:
    """Start a new symptom checker session."""
    try:
        resp = _post("/symptom-checker/start", {"language": language})
        return resp
    except Exception as exc:
        return {"detail": str(exc)}


def answer_symptom_checker(session_id: str, question_id: str, answer: str) -> dict:
    """Submit an answer to the symptom checker."""
    try:
        resp = _post("/symptom-checker/answer", {
            "session_id": session_id,
            "question_id": question_id,
            "answer": answer,
        })
        return resp
    except Exception as exc:
        return {"detail": str(exc)}


def get_symptom_result(session_id: str) -> dict:
    """Get the final triage assessment."""
    try:
        resp = _get(f"/symptom-checker/result/{session_id}")
        return resp
    except Exception as exc:
        return {"detail": str(exc)}


def get_outbreaks(region: str = None) -> dict:
    """Get WHO outbreak alerts."""
    try:
        params = {}
        if region:
            params["region"] = region
        resp = _get("/outbreaks", params=params)
        return resp
    except Exception as exc:
        return {"alerts": [], "detail": str(exc)}


def add_medication(name: str, dosage: str, frequency: str, times: list = None,
                   start_date: str = None, end_date: str = None, notes: str = None,
                   patient_id: int = None) -> dict:
    """Add a medication reminder."""
    try:
        payload = {
            "name": name, "dosage": dosage, "frequency": frequency,
            "times": times or [], "start_date": start_date,
            "end_date": end_date, "notes": notes, "patient_id": patient_id
        }
        return _post("/medications", payload)
    except Exception as exc:
        return {"detail": str(exc)}


def get_medications(patient_id: int = None) -> dict:
    """Get all medication reminders for current user, optionally filtered by patient."""
    try:
        params = {"patient_id": patient_id} if patient_id else {}
        return _get("/medications", params=params)
    except Exception as exc:
        return {"medications": [], "detail": str(exc)}


def delete_medication(med_id: int) -> dict:
    """Delete a medication reminder."""
    try:
        return _delete(f"/medications/{med_id}")
    except Exception as exc:
        return {"detail": str(exc)}


def get_me() -> dict:
    """Get the current authenticated user's profile."""
    if config.BACKEND_CONNECTED:
        try:
            return _get("/auth/me")
        except Exception:
            pass
    return {"username": st.session_state.get("username", "user"), "email": "", "is_admin": False}

