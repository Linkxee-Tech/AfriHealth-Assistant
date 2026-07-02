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


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
def stream_chat(query: str, language: str):
    """Yields response chunks. Maps to POST /chat/stream once backend is live."""
    if config.BACKEND_CONNECTED:
        try:
            with requests.post(
                f"{config.BACKEND_BASE_URL}/chat/stream",
                json={"query": query, "language": language},
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
def save_session(messages):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.post(
                f"{config.BACKEND_BASE_URL}/chat/history", json={"messages": messages}, timeout=10
            )
            return resp.json().get("session_id")
        except requests.RequestException:
            pass
    return db.save_session(messages)


def list_sessions(limit=20):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(
                f"{config.BACKEND_BASE_URL}/chat/history", params={"limit": limit}, timeout=10
            )
            return resp.json()
        except requests.RequestException:
            pass
    return db.list_sessions(limit=limit)


def load_session(session_id):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(
                f"{config.BACKEND_BASE_URL}/chat/history/{session_id}", timeout=10
            )
            return resp.json()
        except requests.RequestException:
            pass
    return db.load_session(session_id)


def delete_session(session_id):
    if config.BACKEND_CONNECTED:
        try:
            requests.delete(f"{config.BACKEND_BASE_URL}/chat/history/{session_id}", timeout=10)
            return
        except requests.RequestException:
            pass
    db.delete_session(session_id)


# ---------------------------------------------------------------------------
# Health metrics  (maps to /metrics GET/POST, /metrics/export GET)
# ---------------------------------------------------------------------------
def add_health_entry(metric_type, value, unit, notes=None):
    if config.BACKEND_CONNECTED:
        try:
            requests.post(
                f"{config.BACKEND_BASE_URL}/metrics",
                json={"metric_type": metric_type, "value": value, "unit": unit, "notes": notes},
                timeout=10,
            )
            return
        except requests.RequestException:
            pass
    db.add_health_entry(metric_type, value, unit)


def get_health_entries(metric_type=None, limit=200):
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(
                f"{config.BACKEND_BASE_URL}/metrics",
                params={"metric_type": metric_type, "limit": limit},
                timeout=10,
            )
            return resp.json()
        except requests.RequestException:
            pass
    return db.get_health_entries(metric_type=metric_type, limit=limit)


def delete_health_entry(entry_id):
    if config.BACKEND_CONNECTED:
        try:
            requests.delete(f"{config.BACKEND_BASE_URL}/metrics/{entry_id}", timeout=10)
            return
        except requests.RequestException:
            pass
    db.delete_health_entry(entry_id)


# ---------------------------------------------------------------------------
# Documents  (maps to /documents/upload, /documents/analyze)
# ---------------------------------------------------------------------------
def analyze_document_stub(filename: str):
    """Placeholder for OCR + RAG interpretation until backend is connected."""
    time.sleep(0.8)
    return {
        "extracted_text": "(Demo) OCR extraction will appear here once easyOCR is connected.",
        "analysis": (
            f"(Demo) AI interpretation of '{filename}' will appear here once the "
            "RAG pipeline is connected to /documents/analyze."
        ),
        "source": "Demo mode",
    }


# ---------------------------------------------------------------------------
# System status  (maps to /health, /status)
# ---------------------------------------------------------------------------
def get_system_status():
    if config.BACKEND_CONNECTED:
        try:
            resp = requests.get(f"{config.BACKEND_BASE_URL}/status", timeout=5)
            return resp.json()
        except requests.RequestException:
            return {"model_loaded": False, "memory_usage_gb": None, "online": False}
    return {"model_loaded": True, "memory_usage_gb": 4.2, "online": False}
