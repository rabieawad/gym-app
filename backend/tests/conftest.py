import os
import tempfile

# Must be set before the app is imported.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["FRONTEND_DIR"] = ""
os.environ["SECRET_KEY"] = "test-secret-test-secret-test-secret-1234"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


_counter = 0


@pytest.fixture()
def make_user(client):
    """Returns a function that registers a fresh user and gives back auth headers."""

    def _make(name="Alex"):
        global _counter
        _counter += 1
        r = client.post(
            "/api/auth/register",
            json={"email": f"user{_counter}@example.com", "display_name": name, "password": "correct horse"},
        )
        assert r.status_code == 201, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _make
