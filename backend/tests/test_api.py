"""API route tests — /health, /status, /chat, /metrics, /chat/history."""

import pytest


def test_health_endpoint(client):
    resp = client.get("/api/v1/system/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "app" in data


def test_status_endpoint(client):
    resp = client.get("/api/v1/system/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "model_loaded" in data
    assert "cpu_percent" in data
    assert "memory_used_gb" in data


def test_chat_endpoint_stub(client):
    resp = client.post(
        "/api/v1/chat",
        json={"query": "What is malaria?", "language": "English"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert len(data["answer"]) > 0


def test_chat_stream_endpoint(client):
    resp = client.post(
        "/api/v1/chat/stream",
        json={"query": "What is malaria?", "language": "English"},
    )
    assert resp.status_code == 200
    # Streaming response — content should be non-empty
    assert len(resp.content) > 0


def test_chat_empty_query_rejected(client):
    resp = client.post("/api/v1/chat", json={"query": "  ", "language": "English"})
    assert resp.status_code == 422


def test_save_and_list_history(client):
    messages = [
        {"role": "user",      "content": "Test question", "sources": []},
        {"role": "assistant", "content": "Test answer",   "sources": ["WHO"]},
    ]
    # Save
    resp = client.post(
        "/api/v1/chat/history",
        json={"messages": messages, "session_id": "test-session-001"},
    )
    assert resp.status_code == 200

    # List
    resp = client.get("/api/v1/chat/history")
    assert resp.status_code == 200
    sessions = resp.json()
    assert isinstance(sessions, list)
    assert any(s["session_id"] == "test-session-001" for s in sessions)


def test_get_session_messages(client):
    resp = client.get("/api/v1/chat/history/test-session-001")
    assert resp.status_code == 200
    msgs = resp.json()
    assert isinstance(msgs, list)
    assert len(msgs) == 2


def test_delete_session(client):
    resp = client.delete("/api/v1/chat/history/test-session-001")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_save_health_metric(client):
    resp = client.post(
        "/api/v1/metrics",
        json={"metric_type": "Heart Rate", "value": "78", "unit": "bpm", "notes": "after rest"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_get_health_metrics(client):
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_export_metrics_csv(client):
    resp = client.get("/api/v1/metrics/export")
    assert resp.status_code == 200
    assert "metric_type" in resp.text


def test_check_vitals_normal(client):
    resp = client.post(
        "/api/v1/metrics/check-vitals",
        json={"metric_type": "Heart Rate", "value": "72"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "normal"
    assert data["urgency"] == "Low"


def test_check_vitals_high(client):
    resp = client.post(
        "/api/v1/metrics/check-vitals",
        json={"metric_type": "Heart Rate", "value": "160"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["urgency"] in ("High", "Emergency", "Medium")


def test_analyze_symptoms(client):
    resp = client.post(
        "/api/v1/metrics/analyze-symptoms",
        json={"symptoms": ["fever", "headache", "cough"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "urgency" in data
    assert "advice" in data


def test_analyze_emergency_symptoms(client):
    resp = client.post(
        "/api/v1/metrics/analyze-symptoms",
        json={"symptoms": ["chest pain", "difficulty breathing"]},
    )
    assert resp.status_code == 200
    assert resp.json()["urgency"] == "Emergency"


def test_list_documents(client):
    resp = client.get("/api/v1/documents")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
