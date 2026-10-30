from app.core.enums import Role
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import PlatformSetting, User
from tests.conftest import PASSWORD, auth


def test_signup_rules(client):
    weak = {"name": "Bad", "email": "bad@gmail.com", "mobile": "9876543210", "password": "weak"}
    assert client.post("/auth/signup", json=weak).status_code == 422

    yahoo = {"name": "Yahoo", "email": "y@yahoo.com", "mobile": "9876543210", "password": PASSWORD}
    r = client.post("/auth/signup", json=yahoo)
    assert r.status_code == 422 and "Gmail" in r.text


def test_signup_login_me(client, accounts):
    user = accounts.make("Asha", "asha@gmail.com")
    me = client.get("/auth/me", headers=user["headers"]).json()
    assert me["email"] == "asha@gmail.com" and me["role"] == "user" and "created_at" in me

    duplicate = {"name": "Asha", "email": "asha@gmail.com", "mobile": "9876543210", "password": PASSWORD}
    assert client.post("/auth/signup", json=duplicate).status_code == 400

    assert (
        client.post("/auth/login", json={"email": "asha@gmail.com", "password": "Wrong@123"}).status_code
        == 401
    )
    r = client.post("/auth/login", json={"email": "ASHA@gmail.com", "password": PASSWORD})
    assert r.status_code == 200 and r.json()["user"]["role"] == "user"
    assert "password" not in r.text  # nothing secret leaks

    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers=auth("not-a-token")).status_code == 401


def test_login_accepts_non_gmail_staff_account(client):
    with SessionLocal() as db:
        db.add(
            User(
                name="Admin",
                email="admin@roomora.com",
                mobile="9876543210",
                password_hash=hash_password("Admin@1234"),
                role=Role.ADMIN,
            )
        )
        db.commit()
    r = client.post("/auth/login", json={"email": "admin@roomora.com", "password": "Admin@1234"})
    assert r.status_code == 200 and r.json()["user"]["role"] == "admin"


def test_blocked_user_cannot_login_or_use_token(client, accounts):
    user = accounts.make("Blocked", "blocked@gmail.com")
    with SessionLocal() as db:
        db.get(User, user["id"]).is_active = False
        db.commit()
    assert (
        client.post("/auth/login", json={"email": "blocked@gmail.com", "password": PASSWORD}).status_code
        == 403
    )
    assert client.get("/auth/me", headers=user["headers"]).status_code == 401


def test_update_profile_and_change_password(client, accounts):
    user = accounts.make("Asha", "asha@gmail.com")
    r = client.patch("/auth/me", headers=user["headers"], json={"name": "Asha K", "location": "Ahmedabad"})
    assert r.status_code == 200 and r.json()["name"] == "Asha K" and r.json()["location"] == "Ahmedabad"

    wrong = {"current_password": "Nope@12345", "new_password": "Newpass@123"}
    assert client.post("/auth/change-password", headers=user["headers"], json=wrong).status_code == 400
    weak = {"current_password": PASSWORD, "new_password": "weakpass"}
    assert client.post("/auth/change-password", headers=user["headers"], json=weak).status_code == 422
    good = {"current_password": PASSWORD, "new_password": "Newpass@123"}
    assert client.post("/auth/change-password", headers=user["headers"], json=good).status_code == 200
    assert (
        client.post("/auth/login", json={"email": "asha@gmail.com", "password": "Newpass@123"}).status_code
        == 200
    )
    assert (
        client.post("/auth/login", json={"email": "asha@gmail.com", "password": PASSWORD}).status_code == 401
    )


def test_registration_can_be_closed_by_platform_setting(client):
    with SessionLocal() as db:
        db.add(PlatformSetting(key="allow_registration", value={"enabled": False}))
        db.commit()
    body = {"name": "Late", "email": "late@gmail.com", "mobile": "9876543210", "password": PASSWORD}
    assert client.post("/auth/signup", json=body).status_code == 403


def test_account_deletion_request_notifies_admins(client, accounts):
    admin = accounts.make("Root", "root@gmail.com", Role.ADMIN)
    user = accounts.make("Asha", "asha@gmail.com")
    assert client.post("/auth/delete-request", headers=user["headers"]).status_code == 200
    assert client.post("/auth/delete-request").status_code == 401
    feed = client.get("/notifications", headers=admin["headers"]).json()["items"]
    assert feed[0]["title"] == "Account deletion requested" and "asha@gmail.com" in feed[0]["body"]
    assert (
        client.get("/auth/me", headers=user["headers"]).status_code == 200
    )  # nothing is deleted automatically
