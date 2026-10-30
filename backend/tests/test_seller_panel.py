import io

from PIL import Image

from app.core.enums import Role
from tests.helpers import deliver_order, setup_shop


def png_bytes(size=(8, 8)):
    out = io.BytesIO()
    Image.new("RGB", size, (140, 145, 101)).save(out, "PNG")
    return out.getvalue()


def test_store_profile_roundtrip(client, accounts):
    user, seller, admin, pid = setup_shop(client, accounts)
    store = client.get("/sellers/me", headers=seller["headers"]).json()
    assert store["store_name"] == "Sam"  # created on first visit, named after the owner
    r = client.put(
        "/sellers/me",
        headers=seller["headers"],
        json={"store_name": "Urban Living", "gst_number": "24ABCDE1234F1Z5", "mobile": "9000000001"},
    )
    assert r.json()["store_name"] == "Urban Living" and r.json()["mobile"] == "9000000001"
    assert client.get("/sellers/me", headers=user["headers"]).status_code == 403


def test_dashboard_inventory_customers_and_analytics(client, accounts):
    user, seller, admin, pid = setup_shop(client, accounts, stock=10)
    deliver_order(client, seller, user, pid, quantity=3)

    board = client.get("/sellers/me/dashboard", headers=seller["headers"]).json()
    assert board["total_products"] == 1 and board["total_orders"] == 1
    assert board["month_revenue"] == 60000 and board["pending_orders"] == 0
    assert board["recent_orders"][0]["product"] == "Teak Sofa" and board["top_products"][0]["sold"] == 3
    assert board["health"]["order_fulfillment"] == 100

    # restock the sold-down product
    assert (
        client.patch(f"/products/{pid}/stock", headers=seller["headers"], json={"stock": 40}).json()["stock"]
        == 40
    )
    assert (
        client.patch(f"/products/{pid}/stock", headers=seller["headers"], json={"stock": -1}).status_code
        == 422
    )
    assert (
        client.patch(f"/products/{pid}/stock", headers=user["headers"], json={"stock": 1}).status_code == 403
    )

    customers = client.get("/sellers/me/customers", headers=seller["headers"]).json()
    assert (
        customers[0]["name"] == "Asha"
        and customers[0]["orders"] == 1
        and customers[0]["total_spent"] == 60000
    )

    analytics = client.get("/sellers/me/analytics", headers=seller["headers"]).json()
    assert len(analytics["monthly_sales"]) == 8 and analytics["monthly_sales"][-1]["value"] == 60000
    assert analytics["categories"][0] == {"category": "Sofa", "revenue": 60000, "percent": 100}


def test_orders_csv_export(client, accounts):
    user, seller, admin, pid = setup_shop(client, accounts, stock=10)
    deliver_order(client, seller, user, pid)
    r = client.get("/sellers/me/export/orders.csv", headers=seller["headers"])
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "Teak Sofa" in r.text and r.text.splitlines()[0].startswith("Order,Date")
    assert client.get("/sellers/me/export/orders.csv", headers=user["headers"]).status_code == 403


def test_image_upload_validation(client, accounts):
    seller = accounts.make("Sam", "sam@gmail.com", Role.SELLER)
    user = accounts.make("Asha", "asha@gmail.com")

    ok = client.post(
        "/uploads/image", headers=seller["headers"], files={"file": ("a.png", png_bytes(), "image/png")}
    )
    assert ok.status_code == 200 and ok.json()["url"].endswith(".png") and ok.json()["url"].startswith("http")
    assert client.get(ok.json()["url"].replace("http://testserver", "")).status_code == 200  # served back

    fake = client.post(
        "/uploads/image", headers=seller["headers"], files={"file": ("a.png", b"not an image", "image/png")}
    )
    assert fake.status_code == 400
    gif = io.BytesIO()
    Image.new("RGB", (4, 4)).save(gif, "GIF")
    assert (
        client.post(
            "/uploads/image",
            headers=seller["headers"],
            files={"file": ("a.gif", gif.getvalue(), "image/gif")},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/uploads/image", headers=user["headers"], files={"file": ("a.png", png_bytes(), "image/png")}
        ).status_code
        == 403
    )
    assert (
        client.post("/uploads/image", files={"file": ("a.png", png_bytes(), "image/png")}).status_code == 401
    )
