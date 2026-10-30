from app.core.enums import Role
from tests.test_products import approved_product

ADDRESS = {
    "full_name": "Asha",
    "mobile": "9876543210",
    "address": "12 MG Road",
    "city": "Ahmedabad",
    "pincode": "380001",
    "payment_method": "UPI",
}  # no State, like the checkout form


def setup_shop(client, accounts, stock=3):
    user = accounts.make("Asha", "asha@gmail.com")
    seller = accounts.make("Sam", "sam@gmail.com", Role.SELLER)
    admin = accounts.make("Root", "root@gmail.com", Role.ADMIN)
    pid = approved_product(client, seller, admin, stock=stock)
    return user, seller, admin, pid


def test_checkout_uses_database_price_and_stock(client, accounts):
    user, seller, admin, pid = setup_shop(client, accounts)

    too_many = {**ADDRESS, "items": [{"product_id": pid, "quantity": 5}]}
    assert (
        client.post("/orders", headers=user["headers"], json=too_many).status_code == 400
    )  # only 3 in stock

    twice = {**ADDRESS, "items": [{"product_id": pid, "quantity": 1}, {"product_id": pid, "quantity": 1}]}
    r = client.post("/orders", headers=user["headers"], json=twice)
    assert r.status_code == 201 and r.json()["total_amount"] == 40000  # 2 x 20000, duplicates merged
    assert len(r.json()["items"]) == 1 and r.json()["items"][0]["quantity"] == 2
    assert client.get(f"/products/{pid}").json()["stock"] == 1

    assert client.post("/orders", json=twice).status_code == 401
    bad_pin = {**ADDRESS, "pincode": "12ab56", "items": [{"product_id": pid, "quantity": 1}]}
    assert client.post("/orders", headers=user["headers"], json=bad_pin).status_code == 422
    assert client.post("/orders", headers=user["headers"], json={**ADDRESS, "items": []}).status_code == 422
    missing = {**ADDRESS, "items": [{"product_id": 9999, "quantity": 1}]}
    assert client.post("/orders", headers=user["headers"], json=missing).status_code == 400
    assert len(client.get("/orders/mine", headers=user["headers"]).json()) == 1


def test_seller_fulfilment_and_customer_cancel(client, accounts):
    user, seller, admin, pid = setup_shop(client, accounts)
    order = client.post(
        "/orders", headers=user["headers"], json={**ADDRESS, "items": [{"product_id": pid, "quantity": 1}]}
    ).json()
    item_id = order["items"][0]["id"]

    rows = client.get("/orders/seller", headers=seller["headers"]).json()
    assert rows[0]["customer_name"] == "Asha" and rows[0]["payment_method"] == "UPI"
    assert client.get("/orders/seller", headers=user["headers"]).status_code == 403

    stranger = accounts.make("Sneaky", "sneaky@gmail.com", Role.SELLER)
    assert (
        client.patch(
            f"/orders/items/{item_id}/status", headers=stranger["headers"], json={"status": "packed"}
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/orders/items/{item_id}/status", headers=seller["headers"], json={"status": "teleported"}
        ).status_code
        == 400
    )
    r = client.patch(f"/orders/items/{item_id}/status", headers=seller["headers"], json={"status": "packed"})
    assert r.json()["status"] == "packed"

    assert (
        client.patch(f"/orders/items/{item_id}/cancel", headers=user["headers"]).status_code == 400
    )  # too late
    assert client.delete(f"/products/{pid}", headers=seller["headers"]).status_code == 400  # has orders


def test_cancel_restocks_and_cod_becomes_paid(client, accounts):
    user, seller, admin, pid = setup_shop(client, accounts, stock=5)
    cod = {**ADDRESS, "payment_method": "COD"}

    first = client.post(
        "/orders", headers=user["headers"], json={**cod, "items": [{"product_id": pid, "quantity": 2}]}
    ).json()
    assert client.get(f"/products/{pid}").json()["stock"] == 3
    cancelled = client.patch(f"/orders/items/{first['items'][0]['id']}/cancel", headers=user["headers"])
    assert cancelled.status_code == 200 and cancelled.json()["items"][0]["status"] == "cancelled"
    assert client.get(f"/products/{pid}").json()["stock"] == 5  # quantity went back on the shelf

    second = client.post(
        "/orders", headers=user["headers"], json={**cod, "items": [{"product_id": pid, "quantity": 1}]}
    ).json()
    item_id = second["items"][0]["id"]
    assert second["payment_status"] == "pending"
    client.patch(f"/orders/items/{item_id}/status", headers=seller["headers"], json={"status": "delivered"})
    mine = client.get("/orders/mine", headers=user["headers"]).json()
    assert next(o for o in mine if o["id"] == second["id"])["payment_status"] == "paid"
    # a delivered item cannot be changed again
    assert (
        client.patch(
            f"/orders/items/{item_id}/status", headers=seller["headers"], json={"status": "cancelled"}
        ).status_code
        == 400
    )
