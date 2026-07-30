"""Shared pytest fixtures for backend tests."""

import pytest
import tempfile
import os
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient


# Configure isolated, lightweight resources before any backend module is
# imported by test collection. This prevents tests from loading the developer's
# local GGUF model or production ChromaDB collection.
TEST_ROOT = Path(tempfile.gettempdir()) / f"afrihealth-tests-{uuid4().hex}"
TEST_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["DB_PATH"] = str(TEST_ROOT / "test_afrihealth.db")
os.environ["MODEL_PATH"] = str(TEST_ROOT / "missing-model.gguf")
os.environ["EMBEDDING_MODEL"] = str(TEST_ROOT / "missing-embedding-model")
os.environ["VECTOR_DB_PATH"] = str(TEST_ROOT / "chroma")
os.environ["SECRET_KEY"] = "test-only-secret-key-with-at-least-32-bytes"


@pytest.fixture(scope="session")
def temp_db(tmp_path_factory):
    """Temporary SQLite database for test isolation."""
    return os.environ["DB_PATH"]


@pytest.fixture(scope="session")
def client(temp_db):
    """FastAPI test client with a fresh database."""
    from backend.main import app
    from backend.database.db_manager import db_manager
    db_manager.init_tables()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth_headers(client):
    username = f"test-user-{uuid4().hex[:8]}"
    response = client.post(
        "/auth/register",
        json={"username": username, "password": "test-password-123"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
