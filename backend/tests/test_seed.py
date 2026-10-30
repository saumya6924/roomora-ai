"""The demo data must stay coherent: every demo login works and every dashboard has content."""

from app.core.enums import OrderItemStatus
from app.db.session import SessionLocal
from app.models import OrderItem, Product, Review
from scripts.seed import seed_all
from tests.conftest import auth


def login(client, email, password):
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"{email}: {r.text}"
    return auth(r.json()["access_token"])


def test_demo_data_fills_every_dashboard(client):
    with SessionLocal() as db:
        seed_all(db)

    admin = login(client, "admin@roomora.com", "Admin@1234")
    seller = login(client, "seller@roomora.com", "Seller@1234")
    designer = login(client, "saumya@roomora.com", "Designer@1234")
    customer = login(client, "user@roomora.com", "User@1234")
    login(client, "nancy@roomora.com", "User@1234")

    board = client.get("/admin/dashboard", headers=admin).json()
    assert board["total_orders"] > 20 and board["total_users"] >= 6 and board["month_revenue"] > 0
    assert len(client.get("/admin/reports", headers=admin).json()["monthly_revenue"]) == 8
    assert any(p["status"] == "requested" for p in client.get("/admin/payouts", headers=admin).json())
    assert len(client.get("/admin/sellers", headers=admin).json()) == 1

    shop = client.get("/sellers/me/dashboard", headers=seller).json()
    assert (
        shop["total_orders"] > 5
        and shop["top_products"]
        and shop["recent_orders"]
        and shop["average_rating"] > 0
    )
    assert client.get("/sellers/me/customers", headers=seller).json()
    assert any(
        m["value"] > 0 for m in client.get("/sellers/me/analytics", headers=seller).json()["monthly_sales"]
    )
    money = client.get("/earnings/me", headers=seller).json()
    assert money["total_earnings"] > 0 and money["available"] > 0
    assert client.get("/payouts/mine", headers=seller).json()

    work = client.get("/designers/me/dashboard", headers=designer).json()
    assert work["pending_requests"] + work["active_projects"] > 0 and work["performance"]["profile_views"] > 0
    assert client.get("/designers/me/services", headers=designer).json()
    assert client.get("/designers/me/portfolio", headers=designer).json()
    assert client.get("/reviews/received", headers=designer).json()["count"] >= 1
    assert client.get("/notifications", headers=designer).json()["items"]

    assert client.get("/orders/mine", headers=customer).json()
    assert len(client.get("/designers").json()) == 6


def test_demo_data_is_consistent(client):
    with SessionLocal() as db:
        seed_all(db)
        # reviews only exist for products that were really delivered to the reviewer
        for review in db.query(Review).filter(Review.product_id.isnot(None)):
            delivered = (
                db.query(OrderItem)
                .filter(
                    OrderItem.product_id == review.product_id, OrderItem.status == OrderItemStatus.DELIVERED
                )
                .count()
            )
            assert delivered >= 1
        assert all(p.stock >= 0 for p in db.query(Product))
