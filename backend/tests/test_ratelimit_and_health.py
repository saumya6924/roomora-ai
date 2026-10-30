from app.core.config import settings


def test_health_reports_database(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["database"] == "ok"


def test_login_is_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    body = {"email": "nobody@gmail.com", "password": "Wrong@1234"}
    codes = [client.post("/auth/login", json=body).status_code for _ in range(7)]
    assert codes[:5] == [401] * 5
    assert codes[5] == 429 and codes[6] == 429
    assert client.post("/auth/login", json=body).headers["retry-after"].isdigit()


def test_ai_editor_is_rate_limited_per_user(client, accounts, monkeypatch):
    user = accounts.make("Ai Tester", "ai@gmail.com")
    other = accounts.make("Other", "other@gmail.com")
    monkeypatch.setattr(settings, "rate_limit_enabled", True)

    def call(who):
        return client.post("/ai/edit-requirements", headers=who["headers"], json={"command": "budget 5000"})

    assert all(call(user).status_code == 200 for _ in range(20))
    assert call(user).status_code == 429
    assert call(other).status_code == 200  # the limit is per user, not global
