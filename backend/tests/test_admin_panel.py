from app.core.enums import Role
from tests.helpers import booking_body, complete_booking, deliver_order, make_designer, setup_shop


def test_dashboard_mixes_orders_and_bookings(client, accounts):
    user, seller, admin, pid = setup_shop(client, accounts, stock=10)
    _, designer, did = make_designer(client, accounts, admin=admin)
    deliver_order(client, seller, user, pid, quantity=1)
    client.post("/bookings", headers=user["headers"], json=booking_body(did, days=2))

    board = client.get("/admin/dashboard", headers=admin["headers"]).json()
    assert board["total_orders"] == 2 and board["pending_requests"] == 1
    assert board["month_revenue"] == 20000 + 7000  # one delivered sofa + a 2-day booking at 3500
    assert board["total_designers"] == 1 and board["designers_available"] == 1
    assert {t["kind"] for t in board["recent_orders"]} == {"Furniture", "Designer"}
    assert board["system"]["ai_engine"] == "rules"
    assert client.get("/admin/dashboard", headers=user["headers"]).status_code == 403


def test_transactions_status_and_exports(client, accounts):
    user, seller, admin, pid = setup_shop(client, accounts, stock=10)
    deliver_order(client, seller, user, pid)
    pending = client.post(
        "/orders",
        headers=user["headers"],
        json={
            "full_name": "Asha",
            "mobile": "9876543210",
            "address": "12 MG Road",
            "city": "Pune",
            "pincode": "411001",
            "items": [{"product_id": pid, "quantity": 1}],
        },
    ).json()
    rows = client.get("/admin/transactions", headers=admin["headers"]).json()
    by_ref = {r["ref"]: r for r in rows}
    assert by_ref["#RM1"]["status"] == "delivered" and by_ref["#RM1"]["payment"] == "paid"
    assert by_ref[f"#RM{pending['id']}"]["status"] == "pending"

    users_csv = client.get("/admin/export/users.csv", headers=admin["headers"])
    assert users_csv.headers["content-type"].startswith("text/csv") and "asha@gmail.com" in users_csv.text
    assert "#RM1" in client.get("/admin/export/orders.csv", headers=admin["headers"]).text
    assert client.get("/admin/export/users.csv", headers=user["headers"]).status_code == 403


def test_users_are_enriched_and_filtered(client, accounts):
    user, seller, admin, pid = setup_shop(client, accounts, stock=10)
    deliver_order(client, seller, user, pid)
    client.post(
        "/auth/login", json={"email": "asha@gmail.com", "password": "Hello@1234"}
    )  # records last login
    rows = {u["email"]: u for u in client.get("/admin/users", headers=admin["headers"]).json()}
    assert rows["asha@gmail.com"]["orders"] == 1 and rows["asha@gmail.com"]["status"] == "active"
    assert rows["asha@gmail.com"]["last_active"] is not None
    assert rows["sam@gmail.com"]["status"] == "inactive"  # never logged in after signup
    client.patch(f"/admin/users/{user['id']}/block", headers=admin["headers"])
    rows = {u["email"]: u for u in client.get("/admin/users", headers=admin["headers"]).json()}
    assert rows["asha@gmail.com"]["status"] == "blocked"


def test_products_designers_sellers_and_bookings_lists(client, accounts):
    user, seller, admin, pid = setup_shop(client, accounts)
    client.put("/sellers/me", headers=seller["headers"], json={"store_name": "Urban Living"})
    _, designer, did = make_designer(client, accounts, admin=admin)
    complete_booking(client, designer, user, did)

    products = client.get("/admin/products", headers=admin["headers"]).json()
    assert products[0]["seller_name"] == "Urban Living" and products[0]["price"] == 20000
    assert client.get("/admin/products?status=pending", headers=admin["headers"]).json() == []
    assert client.get("/admin/products?status=bogus", headers=admin["headers"]).status_code == 400

    designers = client.get("/admin/designers", headers=admin["headers"]).json()
    assert designers[0]["projects"] == 1 and designers[0]["availability"] == "available"
    client.patch("/designers/me/availability", headers=designer["headers"])
    assert client.get("/admin/designers", headers=admin["headers"]).json()[0]["availability"] == "offline"

    sellers = client.get("/admin/sellers", headers=admin["headers"]).json()
    assert sellers[0]["business"] == "Urban Living" and sellers[0]["products"] == 1
    assert (
        client.patch(
            f"/admin/sellers/{seller['id']}/status", headers=admin["headers"], json={"status": "suspended"}
        ).status_code
        == 200
    )
    assert client.get("/admin/sellers", headers=admin["headers"]).json()[0]["status"] == "suspended"
    assert (
        client.patch(
            f"/admin/sellers/{user['id']}/status", headers=admin["headers"], json={"status": "active"}
        ).status_code
        == 404
    )

    bookings = client.get("/admin/bookings", headers=admin["headers"]).json()
    assert bookings[0]["designer"] == "Dia Designer" and bookings[0]["status"] == "completed"


def test_reports_and_platform_settings(client, accounts):
    user, seller, admin, pid = setup_shop(client, accounts, stock=10)
    deliver_order(client, seller, user, pid)
    report = client.get("/admin/reports", headers=admin["headers"]).json()
    assert len(report["monthly_revenue"]) == 8 and report["monthly_revenue"][-1]["value"] == 20000
    assert report["furniture_percent"] == 100 and report["designer_percent"] == 0

    flags = client.get("/admin/settings", headers=admin["headers"]).json()
    assert flags["allow_registration"] is True
    assert (
        client.put("/admin/settings", headers=admin["headers"], json={"allow_registration": False}).json()[
            "allow_registration"
        ]
        is False
    )
    body = {"name": "Late", "email": "late@gmail.com", "mobile": "9876543210", "password": "Hello@1234"}
    assert client.post("/auth/signup", json=body).status_code == 403  # the switch is enforced by the backend
    assert client.put("/admin/settings", headers=admin["headers"], json={"nonsense": True}).status_code == 400
    assert (
        client.put("/admin/settings", headers=user["headers"], json={"allow_registration": True}).status_code
        == 403
    )
    assert Role.ADMIN.value == "admin"
