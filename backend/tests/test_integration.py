"""Cross-module API workflow checks corresponding to the integration checklist."""


def test_conversation_alias_and_clinical_workflow(client, auth_headers):
    saved = client.post("/chat/history", json={"messages": [{"role": "user", "content": "fever"}]}, headers=auth_headers)
    assert saved.status_code == 200
    conversations = client.get("/conversations", headers=auth_headers)
    assert conversations.status_code == 200
    assert isinstance(conversations.json(), list)

    guidelines = client.get("/clinical/guidelines", headers=auth_headers)
    assert guidelines.status_code == 200
    assert guidelines.json()
    drugs = client.get("/clinical/drugs", params={"query": "para"}, headers=auth_headers)
    assert drugs.status_code == 200
    assert any(item["name"] == "paracetamol" for item in drugs.json())
    bmi = client.post("/clinical/calculators/bmi", json={"height_cm": 170, "weight_kg": 70}, headers=auth_headers)
    assert bmi.status_code == 200
    assert bmi.json()["bmi"] > 0
