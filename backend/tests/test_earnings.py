from tests.helpers import complete_booking, deliver_order, make_designer, setup_shop


def test_seller_balance_and_payout_flow(client, accounts):
    user, seller, admin, pid = setup_shop(client, accounts, stock=10)
    assert client.get("/earnings/me", headers=seller["headers"]).json()["available"] == 0
    assert (
        client.post("/payouts", headers=seller["headers"], json={}).status_code == 400
    )  # nothing to pay out

    deliver_order(client, seller, user, pid, quantity=2)  # 2 x 20000
    earnings = client.get("/earnings/me", headers=seller["headers"]).json()
    assert earnings["total_earnings"] == 40000 and earnings["available"] == 40000

    assert client.post("/payouts", headers=seller["headers"], json={"amount": 50000}).status_code == 400
    r = client.post("/payouts", headers=seller["headers"], json={"amount": 15000})
    assert (
        r.status_code == 201
        and r.json()["status"] == "requested"
        and r.json()["reference"].startswith("PAY-")
    )
    payout_id = r.json()["id"]
    earnings = client.get("/earnings/me", headers=seller["headers"]).json()
    assert earnings["available"] == 25000 and earnings["pending_payout"] == 15000

    assert (
        client.patch(
            f"/admin/payouts/{payout_id}", headers=seller["headers"], json={"status": "completed"}
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/admin/payouts/{payout_id}", headers=admin["headers"], json={"status": "teleported"}
        ).status_code
        == 400
    )
    done = client.patch(f"/admin/payouts/{payout_id}", headers=admin["headers"], json={"status": "completed"})
    assert done.status_code == 200 and done.json()["processed_at"] is not None
    assert (
        client.patch(
            f"/admin/payouts/{payout_id}", headers=admin["headers"], json={"status": "rejected"}
        ).status_code
        == 400
    )

    earnings = client.get("/earnings/me", headers=seller["headers"]).json()
    assert (
        earnings["paid_out"] == 15000 and earnings["available"] == 25000 and earnings["pending_payout"] == 0
    )
    assert client.get("/payouts/mine", headers=seller["headers"]).json()[0]["status"] == "completed"
    assert any(
        n["title"].startswith("Payout")
        for n in client.get("/notifications", headers=seller["headers"]).json()["items"]
    )
    assert client.get("/earnings/me", headers=user["headers"]).status_code == 403


def test_rejected_payout_returns_the_money(client, accounts):
    user, seller, admin, pid = setup_shop(client, accounts, stock=10)
    deliver_order(client, seller, user, pid)
    payout = client.post("/payouts", headers=seller["headers"], json={}).json()  # everything available
    assert client.get("/earnings/me", headers=seller["headers"]).json()["available"] == 0
    client.patch(f"/admin/payouts/{payout['id']}", headers=admin["headers"], json={"status": "rejected"})
    assert client.get("/earnings/me", headers=seller["headers"]).json()["available"] == 20000


def test_designer_earns_from_completed_bookings(client, accounts):
    admin, designer, did = make_designer(client, accounts, price=3500)
    user = accounts.make("Asha", "asha@gmail.com")
    complete_booking(client, designer, user, did, days=2)
    earnings = client.get("/earnings/me", headers=designer["headers"]).json()
    assert earnings["total_earnings"] == 7000 and earnings["this_month"] == 7000
    assert client.post("/payouts", headers=designer["headers"], json={"amount": 7000}).status_code == 201
