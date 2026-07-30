from uuid import uuid4


def test_local_password_recovery_is_one_time(client):
    username = f"recover-{uuid4().hex[:8]}"
    old_password = "old-password-123"
    new_password = "new-password-456"
    registered = client.post("/auth/register", json={"username": username, "password": old_password, "email": f"{username}@example.test"})
    assert registered.status_code == 200

    request = client.post("/auth/forgot-password", json={"username": username.lower()})
    assert request.status_code == 200
    token = request.json().get("recovery_token")
    assert token
    assert 6 <= len(token) <= 8

    reset = client.post("/auth/reset-password", json={"token": token, "new_password": new_password})
    assert reset.status_code == 200
    reused = client.post("/auth/reset-password", json={"token": token, "new_password": old_password})
    assert reused.status_code == 400

    login = client.post("/auth/login", data={"username": username, "password": new_password})
    assert login.status_code == 200


def test_unknown_recovery_request_does_not_disclose_account(client):
    response = client.post("/auth/forgot-password", json={"username": "does-not-exist"})
    assert response.status_code == 200
    assert "recovery_token" not in response.json()
