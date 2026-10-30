"""Shared test setup: a throwaway SQLite database and small helpers.

Settings are read when the app is imported, so the environment must be prepared first.
"""

import os
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_tmp) / "test.db")
os.environ["MEDIA_DIR"] = str(Path(_tmp) / "media")
os.environ["ANTHROPIC_API_KEY"] = ""  # force the offline rules engine
os.environ["SUPABASE_URL"] = ""
os.environ["RATE_LIMIT_ENABLED"] = "false"  # tests that check limits switch it back on

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.enums import Role  # noqa: E402
from app.core.ratelimit import reset_limits  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402

PASSWORD = "Hello@1234"


@pytest.fixture(autouse=True)
def fresh_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    reset_limits()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class Accounts:
    """Creates users through the real signup route, then promotes them directly in the database."""

    def __init__(self, client: TestClient):
        self.client = client

    def make(self, name: str, email: str, role: Role = Role.USER) -> dict:
        r = self.client.post(
            "/auth/signup",
            json={"name": name, "email": email, "mobile": "9876543210", "password": PASSWORD},
        )
        assert r.status_code == 201, r.text
        data = r.json()
        if role != Role.USER:
            with SessionLocal() as db:
                db.get(User, data["user"]["id"]).role = role
                db.commit()
        return {
            "token": data["access_token"],
            "id": data["user"]["id"],
            "headers": auth(data["access_token"]),
        }


@pytest.fixture
def accounts(client):
    return Accounts(client)
