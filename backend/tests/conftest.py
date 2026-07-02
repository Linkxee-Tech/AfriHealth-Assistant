"""Shared pytest fixtures for backend tests."""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def temp_db(tmp_path_factory):
    """Temporary SQLite database for test isolation."""
    db_file = str(tmp_path_factory.mktemp("db") / "test_afrihealth.db")
    os.environ["DB_PATH"] = db_file
    return db_file


@pytest.fixture(scope="session")
def client(temp_db):
    """FastAPI test client with a fresh database."""
    from backend.main import app
    from backend.database.db_manager import db_manager
    db_manager.init_tables()
    with TestClient(app) as c:
        yield c
