from app.core.enums import Role
from app.db.session import SessionLocal
from app.models import DesignerProfile, SellerProfile
from tests.test_orders import ADDRESS, setup_shop


def test_stats_require_admin_and_reflect_orders(client, accounts):
    user, seller, admin, pid = setup_shop(client, accounts)
    client.post(
        "/orders", headers=user["headers"], json={**ADDRESS, "items": [{"product_id": pid, "quantity": 2}]}
    )

    assert client.get("/admin/stats", headers=user["headers"]).status_code == 403
    assert client.get("/admin/stats").status_code == 401
    stats = client.get("/admin/stats", headers=admin["headers"]).json()
    assert stats["total_orders"] == 1 and stats["revenue_inr"] == 40000
    assert stats["total_sellers"] == 1 and stats["total_users"] == 1
    assert len(client.get("/admin/orders", headers=admin["headers"]).json()) == 1


def test_user_search_filters_and_role_change(client, accounts):
    admin = accounts.make("Root", "root@gmail.com", Role.ADMIN)
    asha = accounts.make("Asha Shah", "asha@gmail.com")
    accounts.make("Bina", "bina@gmail.com")

    assert len(client.get("/admin/users?search=asha", headers=admin["headers"]).json()) == 1
    assert len(client.get("/admin/users?role=admin", headers=admin["headers"]).json()) == 1
    assert client.get("/admin/users?role=wizard", headers=admin["headers"]).status_code == 400

    assert (
        client.patch(
            f"/admin/users/{asha['id']}/role", headers=admin["headers"], json={"role": "wizard"}
        ).status_code
        == 400
    )
    r = client.patch(f"/admin/users/{asha['id']}/role", headers=admin["headers"], json={"role": "designer"})
    assert r.json()["role"] == "designer"
    assert (
        client.patch(
            f"/admin/users/{admin['id']}/role", headers=admin["headers"], json={"role": "user"}
        ).status_code
        == 400
    )


def test_promoting_to_designer_or_seller_creates_their_profile(client, accounts):
    admin = accounts.make("Root", "root@gmail.com", Role.ADMIN)
    d = accounts.make("Dee", "dee@gmail.com")
    s = accounts.make("Sid", "sid@gmail.com")
    client.patch(f"/admin/users/{d['id']}/role", headers=admin["headers"], json={"role": "designer"})
    client.patch(f"/admin/users/{s['id']}/role", headers=admin["headers"], json={"role": "seller"})
    with SessionLocal() as db:
        assert db.query(DesignerProfile).filter_by(user_id=d["id"]).one().status.value == "pending"
        assert db.query(SellerProfile).filter_by(user_id=s["id"]).one().store_name == "Sid"


def test_block_and_unblock(client, accounts):
    admin = accounts.make("Root", "root@gmail.com", Role.ADMIN)
    user = accounts.make("Asha", "asha@gmail.com")
    assert client.patch(f"/admin/users/{admin['id']}/block", headers=admin["headers"]).status_code == 400
    assert (
        client.patch(f"/admin/users/{user['id']}/block", headers=admin["headers"]).json()["is_active"]
        is False
    )
    assert client.get("/auth/me", headers=user["headers"]).status_code == 401
    assert (
        client.patch(f"/admin/users/{user['id']}/block", headers=admin["headers"]).json()["is_active"] is True
    )
    assert client.patch("/admin/users/9999/block", headers=admin["headers"]).status_code == 404
