"""Scenario builders shared by the test files."""

from app.core.enums import Role
from tests.test_designers import booking_body, make_designer
from tests.test_orders import ADDRESS, setup_shop


def deliver_order(client, seller, user, pid, quantity=1, method="COD"):
    """Place an order and walk it through to delivered. Returns the order json."""
    order = client.post(
        "/orders",
        headers=user["headers"],
        json={**ADDRESS, "payment_method": method, "items": [{"product_id": pid, "quantity": quantity}]},
    ).json()
    item_id = order["items"][0]["id"]
    for status in ("packed", "shipped", "delivered"):
        r = client.patch(
            f"/orders/items/{item_id}/status", headers=seller["headers"], json={"status": status}
        )
        assert r.status_code == 200, r.text
    return order


def complete_booking(client, designer, user, did, days=3):
    bid = client.post("/bookings", headers=user["headers"], json=booking_body(did, days=days)).json()["id"]
    for status in ("accepted", "completed"):
        r = client.patch(f"/bookings/{bid}/status", headers=designer["headers"], json={"status": status})
        assert r.status_code == 200, r.text
    return bid


__all__ = [
    "ADDRESS",
    "Role",
    "booking_body",
    "complete_booking",
    "deliver_order",
    "make_designer",
    "setup_shop",
]
