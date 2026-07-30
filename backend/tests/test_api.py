"""API route tests — /health, /status, /chat, /metrics, /chat/history."""

import pytest


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "app" in data


def test_api_v1_health_cors_preflight(client):
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_status_endpoint(client):
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "model_loaded" in data
    assert "cpu_percent" in data
    assert "memory_used_gb" in data


def test_chat_endpoint_stub(client, auth_headers):
    resp = client.post(
        "/chat",
        json={"query": "What is malaria?", "language": "English"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert len(data["answer"]) > 0


def test_chat_stream_endpoint(client, auth_headers):
    resp = client.post(
        "/chat/stream",
        json={"query": "What is malaria?", "language": "English"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    # Streaming response — content should be non-empty
    assert len(resp.content) > 0


def test_chat_empty_query_rejected(client, auth_headers):
    resp = client.post("/chat", json={"query": "  ", "language": "English"}, headers=auth_headers)
    assert resp.status_code == 422


def test_save_and_list_history(client, auth_headers):
    messages = [
        {"role": "user",      "content": "Test question", "sources": []},
        {"role": "assistant", "content": "Test answer",   "sources": ["WHO"]},
    ]
    # Save
    resp = client.post(
        "/chat/history",
        json={"messages": messages, "session_id": "test-session-001"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # List
    resp = client.get("/chat/history", headers=auth_headers)
    assert resp.status_code == 200
    sessions = resp.json()
    assert isinstance(sessions, list)
    assert any(s["session_id"] == "test-session-001" for s in sessions)


def test_get_session_messages(client, auth_headers):
    resp = client.get("/chat/history/test-session-001", headers=auth_headers)
    assert resp.status_code == 200
    msgs = resp.json()
    assert isinstance(msgs, list)
    assert len(msgs) == 2


def test_delete_session(client, auth_headers):
    resp = client.delete("/chat/history/test-session-001", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_save_health_metric(client, auth_headers):
    resp = client.post(
        "/metrics",
        json={"metric_type": "Heart Rate", "value": "78", "unit": "bpm", "notes": "after rest"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_get_health_metrics(client, auth_headers):
    resp = client.get("/metrics", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json().get("metrics"), list)


def test_export_metrics_csv(client, auth_headers):
    resp = client.get("/metrics/export", headers=auth_headers)
    assert resp.status_code == 200
    assert "metric_type" in resp.text


def test_check_vitals_normal(client):
    resp = client.post(
        "/metrics/check-vitals",
        json={"metric_type": "Heart Rate", "value": "72"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "normal"
    assert data["urgency"] == "Low"


def test_check_vitals_high(client):
    resp = client.post(
        "/metrics/check-vitals",
        json={"metric_type": "Heart Rate", "value": "160"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["urgency"] in ("High", "Emergency", "Medium")


def test_analyze_symptoms(client):
    resp = client.post(
        "/metrics/analyze-symptoms",
        json={"symptoms": ["fever", "headache", "cough"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "urgency" in data
    assert "advice" in data


def test_analyze_emergency_symptoms(client):
    resp = client.post(
        "/metrics/analyze-symptoms",
        json={"symptoms": ["chest pain", "difficulty breathing"]},
    )
    assert resp.status_code == 200
    assert resp.json()["urgency"] == "Emergency"


def test_list_documents(client, auth_headers):
    resp = client.get("/documents", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_patient_search_visit_update_and_export(client, auth_headers):
    patient = client.post(
        "/patients",
        json={
            "first_name": "Amina",
            "last_name": "Okafor",
            "gender": "Female",
            "phone": "08000000000",
        },
        headers=auth_headers,
    )
    assert patient.status_code == 200
    patient_id = patient.json()["patient_id"]

    search = client.get("/patients/search", params={"search": "Amina"}, headers=auth_headers)
    assert search.status_code == 200
    assert any(item["id"] == patient_id for item in search.json())

    visit = client.post(
        f"/patients/{patient_id}/visits",
        json={"chief_complaint": "fever", "visit_type": "Initial"},
        headers=auth_headers,
    )
    assert visit.status_code == 200
    visit_id = visit.json()["visit_id"]

    update = client.put(
        f"/visits/{visit_id}",
        json={"diagnosis": "Febrile illness", "notes": "Follow up if persistent"},
        headers=auth_headers,
    )
    assert update.status_code == 200

    exported = client.get(f"/patients/{patient_id}/export", headers=auth_headers)
    assert exported.status_code == 200
    assert exported.json()["patient"]["id"] == patient_id
    assert exported.json()["visits"][0]["diagnosis"] == "Febrile illness"

    pdf = client.get(f"/patients/{patient_id}/export/pdf", headers=auth_headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content.startswith(b"%PDF")


def test_settings_and_local_backup_are_persistent_and_authenticated(client, auth_headers):
    update = client.put(
        "/settings",
        json={"preferred_language": "Yoruba", "max_tokens": 768},
        headers=auth_headers,
    )
    assert update.status_code == 200
    assert update.json()["preferred_language"] == "Yoruba"
    assert client.get("/settings", headers=auth_headers).json()["max_tokens"] == "768"

    backup = client.get("/online/backup", headers=auth_headers)
    assert backup.status_code == 200
    assert backup.headers["content-type"].startswith("application/json")
    assert backup.json()["format"] == "afrihealth-user-backup"


def test_empty_drug_interaction_request_is_bad_request(client, auth_headers):
    resp = client.post("/clinical/drugs/interact", json={}, headers=auth_headers)
    assert resp.status_code == 400
