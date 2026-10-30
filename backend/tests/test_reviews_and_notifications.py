from tests.helpers import complete_booking, deliver_order, make_designer, setup_shop


def test_product_review_needs_a_delivered_order(client, accounts):
    user, seller, admin, pid = setup_shop(client, accounts, stock=5)
    review = {"product_id": pid, "rating": 5, "title": "Lovely", "body": "Great sofa"}

    assert client.post("/reviews", json=review).status_code == 401
    assert client.post("/reviews", headers=user["headers"], json=review).status_code == 403  # never bought it

    deliver_order(client, seller, user, pid)
    r = client.post("/reviews", headers=user["headers"], json=review)
    assert r.status_code == 201 and r.json()["customer_name"] == "Asha" and r.json()["subject"] == "Teak Sofa"
    assert client.post("/reviews", headers=user["headers"], json=review).status_code == 400  # only once
    assert client.post("/reviews", headers=user["headers"], json={**review, "rating": 6}).status_code == 422
    assert (
        client.post("/reviews", headers=user["headers"], json={"rating": 5}).status_code == 422
    )  # no target

    assert len(client.get(f"/products/{pid}/reviews").json()) == 1
    assert client.get("/reviews/mine", headers=user["headers"]).json()[0]["product_id"] == pid

    summary = client.get("/reviews/received", headers=seller["headers"]).json()
    assert summary["count"] == 1 and summary["average"] == 5 and summary["distribution"]["5"] == 100
    assert client.get("/reviews/received", headers=user["headers"]).status_code == 403


def test_designer_review_needs_a_completed_booking(client, accounts):
    admin, designer, did = make_designer(client, accounts)
    user = accounts.make("Asha", "asha@gmail.com")
    review = {"designer_id": did, "rating": 4, "body": "Good"}
    assert client.post("/reviews", headers=user["headers"], json=review).status_code == 403

    complete_booking(client, designer, user, did)
    assert client.post("/reviews", headers=user["headers"], json=review).status_code == 201
    summary = client.get("/reviews/received", headers=designer["headers"]).json()
    assert summary["count"] == 1 and summary["average"] == 4
    assert client.get(f"/designers/{did}/reviews").json()[0]["rating"] == 4


def test_notifications_follow_the_order_lifecycle(client, accounts):
    user, seller, admin, pid = setup_shop(client, accounts, stock=5)
    deliver_order(
        client, seller, user, pid, quantity=4
    )  # leaves 1 in stock: below the default threshold of 5

    seller_feed = client.get("/notifications", headers=seller["headers"]).json()
    titles = [n["title"] for n in seller_feed["items"]]
    assert "New order received" in titles and "Low stock alert" in titles
    assert seller_feed["unread"] == len(seller_feed["items"])

    buyer_feed = client.get("/notifications", headers=user["headers"]).json()
    assert any("delivered" in n["body"] for n in buyer_feed["items"])

    first = seller_feed["items"][0]["id"]
    assert client.patch(f"/notifications/{first}/read", headers=seller["headers"]).status_code == 200
    assert (
        client.patch(f"/notifications/{first}/read", headers=user["headers"]).status_code == 404
    )  # not theirs
    assert client.post("/notifications/read-all", headers=seller["headers"]).status_code == 200
    assert client.get("/notifications", headers=seller["headers"]).json()["unread"] == 0
    assert client.get("/notifications").status_code == 401


def test_booking_and_product_decisions_notify(client, accounts):
    admin, designer, did = make_designer(client, accounts)
    user = accounts.make("Asha", "asha@gmail.com")
    from tests.test_designers import booking_body

    bid = client.post("/bookings", headers=user["headers"], json=booking_body(did)).json()["id"]
    assert (
        client.get("/notifications", headers=designer["headers"]).json()["items"][0]["title"]
        == "New booking request"
    )
    client.patch(f"/bookings/{bid}/status", headers=designer["headers"], json={"status": "accepted"})
    assert (
        client.get("/notifications", headers=user["headers"]).json()["items"][0]["title"]
        == "Booking accepted"
    )
