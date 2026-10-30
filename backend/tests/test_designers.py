from app.core.enums import Role
from app.db.session import SessionLocal
from app.models import PlatformSetting


def make_designer(client, accounts, price=3500):
    admin = accounts.make("Root", "root@gmail.com", Role.ADMIN)
    designer = accounts.make("Dia Designer", "dia@gmail.com")
    r = client.post(
        "/designers",
        headers=admin["headers"],
        json={"user_id": designer["id"], "speciality": "Cafes", "price_per_day": price},
    )
    assert r.status_code == 201, r.text
    return admin, designer, r.json()["id"]


def booking_body(designer_id, **overrides):
    return {
        "designer_id": designer_id,
        "name": "Asha",
        "mobile": "9876543210",
        "email": "asha@gmail.com",
        "project_type": "Cafe",
        "start_date": "2026-11-05",
        "days": 3,
        "details": "Cozy cafe",
        **overrides,
    }


def test_designer_listing_and_booking_flow(client, accounts):
    admin, designer, did = make_designer(client, accounts)
    user = accounts.make("Asha", "asha@gmail.com")

    listing = client.get("/designers").json()
    assert listing[0]["name"] == "Dia Designer" and listing[0]["price_per_day"] == 3500

    assert client.post("/bookings", json=booking_body(did)).status_code == 401
    r = client.post("/bookings", headers=user["headers"], json=booking_body(did))
    assert r.status_code == 201 and r.json()["total_amount"] == 10500  # 3500 x 3
    bid = r.json()["id"]
    assert (
        client.post("/bookings", headers=user["headers"], json=booking_body(did, days=61)).status_code == 422
    )

    assert client.get("/bookings/designer", headers=designer["headers"]).json()[0]["id"] == bid
    assert client.get("/bookings/designer", headers=user["headers"]).status_code == 403
    assert client.get("/bookings/mine", headers=user["headers"]).json()[0]["id"] == bid

    # a customer cannot answer their own booking; the designer follows pending -> accepted -> completed
    assert (
        client.patch(
            f"/bookings/{bid}/status", headers=user["headers"], json={"status": "accepted"}
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/bookings/{bid}/status", headers=designer["headers"], json={"status": "completed"}
        ).status_code
        == 400
    )
    r = client.patch(f"/bookings/{bid}/status", headers=designer["headers"], json={"status": "accepted"})
    assert r.json()["status"] == "accepted"
    r = client.patch(f"/bookings/{bid}/status", headers=designer["headers"], json={"status": "completed"})
    assert r.json()["status"] == "completed"


def test_designer_cannot_touch_another_designers_booking(client, accounts):
    admin, designer, did = make_designer(client, accounts)
    user = accounts.make("Asha", "asha@gmail.com")
    bid = client.post("/bookings", headers=user["headers"], json=booking_body(did)).json()["id"]

    rival = accounts.make("Rival", "rival@gmail.com")
    client.post("/designers", headers=admin["headers"], json={"user_id": rival["id"], "price_per_day": 1000})
    r = client.patch(f"/bookings/{bid}/status", headers=rival["headers"], json={"status": "accepted"})
    assert r.status_code == 403


def test_availability_and_status_controls(client, accounts):
    admin, designer, did = make_designer(client, accounts)
    user = accounts.make("Asha", "asha@gmail.com")

    assert (
        client.patch("/designers/me/availability", headers=designer["headers"]).json()["is_available"]
        is False
    )
    assert client.post("/bookings", headers=user["headers"], json=booking_body(did)).status_code == 400
    client.patch("/designers/me/availability", headers=designer["headers"])

    assert (
        client.patch(
            f"/designers/{did}/status", headers=user["headers"], json={"status": "suspended"}
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/designers/{did}/status", headers=admin["headers"], json={"status": "nope"}
        ).status_code
        == 400
    )
    client.patch(f"/designers/{did}/status", headers=admin["headers"], json={"status": "suspended"})
    assert client.get("/designers").json() == []
    assert client.post("/bookings", headers=user["headers"], json=booking_body(did)).status_code == 404


def test_bookings_can_be_closed_by_platform_setting(client, accounts):
    admin, designer, did = make_designer(client, accounts)
    user = accounts.make("Asha", "asha@gmail.com")
    with SessionLocal() as db:
        db.add(PlatformSetting(key="designer_bookings_enabled", value={"enabled": False}))
        db.commit()
    assert client.post("/bookings", headers=user["headers"], json=booking_body(did)).status_code == 403
