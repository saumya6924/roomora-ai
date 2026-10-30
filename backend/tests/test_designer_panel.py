from tests.helpers import booking_body, complete_booking, make_designer


def test_profile_services_and_price_sync(client, accounts):
    admin, designer, did = make_designer(client, accounts, price=3500)
    user = accounts.make("Asha", "asha@gmail.com")

    me = client.get("/designers/me", headers=designer["headers"]).json()
    assert me["name"] == "Dia Designer" and me["projects_completed"] == 0 and me["response_rate"] is None
    assert client.get("/designers/me", headers=user["headers"]).status_code == 403

    r = client.put(
        "/designers/me",
        headers=designer["headers"],
        json={
            "title": "Interior Designer",
            "location": "Mumbai",
            "about": "Warm modern spaces",
            "experience": "5 - 10 Years",
        },
    )
    assert r.json()["location"] == "Mumbai" and r.json()["experience"] == "5 - 10 Years"

    # services: the cheapest active per-day service sets the day rate that bookings are priced from
    svc = client.post(
        "/designers/me/services",
        headers=designer["headers"],
        json={"category": "RESIDENTIAL", "name": "Room Redesign", "price": 2500, "unit": "day"},
    )
    assert svc.status_code == 201
    client.post(
        "/designers/me/services",
        headers=designer["headers"],
        json={"name": "Design Consultation", "price": 900, "unit": "session"},
    )  # not per day
    assert client.get("/designers/me", headers=designer["headers"]).json()["price_per_day"] == 2500
    booking = client.post("/bookings", headers=user["headers"], json=booking_body(did, days=2)).json()
    assert booking["total_amount"] == 5000

    sid = svc.json()["id"]
    assert (
        client.put(
            f"/designers/me/services/{sid}",
            headers=designer["headers"],
            json={"name": "Room Redesign", "price": 3000, "unit": "day"},
        ).json()["price"]
        == 3000
    )
    assert len(client.get("/designers/me/services", headers=designer["headers"]).json()) == 2
    assert client.delete(f"/designers/me/services/{sid}", headers=user["headers"]).status_code == 403
    assert client.delete(f"/designers/me/services/{sid}", headers=designer["headers"]).status_code == 200
    assert (
        client.post(
            "/designers/me/services", headers=designer["headers"], json={"name": "X", "price": 0}
        ).status_code
        == 422
    )


def test_portfolio_and_public_profile(client, accounts):
    admin, designer, did = make_designer(client, accounts)
    item = client.post(
        "/designers/me/portfolio",
        headers=designer["headers"],
        json={
            "title": "Minimal Cafe Concept",
            "category": "COMMERCIAL",
            "location": "Ahmedabad",
            "area_sqft": 1200,
        },
    )
    assert item.status_code == 201
    other = accounts.make("Rival", "rival@gmail.com")
    client.post("/designers", headers=admin["headers"], json={"user_id": other["id"], "price_per_day": 1000})
    assert (
        client.delete(f"/designers/me/portfolio/{item.json()['id']}", headers=other["headers"]).status_code
        == 404
    )

    profile = client.get(f"/designers/{did}").json()
    assert profile["name"] == "Dia Designer" and profile["portfolio"][0]["title"] == "Minimal Cafe Concept"
    assert "email" not in profile and "ifsc" not in profile  # private fields never go public
    client.get(f"/designers/{did}")
    assert (
        client.get("/designers/me", headers=designer["headers"]).status_code == 200
    )  # "me" is not read as an id
    dash = client.get("/designers/me/dashboard", headers=designer["headers"]).json()
    assert dash["performance"]["profile_views"] == 2

    client.put("/designers/me", headers=designer["headers"], json={"is_visible": False})
    assert client.get(f"/designers/{did}").status_code == 404
    assert (
        client.get("/designers").json()[0]["name"] != "Dia Designer"
        if client.get("/designers").json()
        else True
    )


def test_dashboard_numbers(client, accounts):
    admin, designer, did = make_designer(client, accounts, price=3000)
    user = accounts.make("Asha", "asha@gmail.com")
    client.post("/bookings", headers=user["headers"], json=booking_body(did))  # stays pending
    complete_booking(client, designer, user, did, days=2)  # 6000, completed

    dash = client.get("/designers/me/dashboard", headers=designer["headers"]).json()
    assert dash["pending_requests"] == 1 and dash["active_projects"] == 0
    assert dash["month_earnings"] == 6000 and dash["performance"]["booking_requests"] == 2
    assert dash["performance"]["conversion_rate"] == 50  # one of two requests was taken on
    assert dash["new_requests"][0]["client"] == "Asha"

    me = client.get("/designers/me", headers=designer["headers"]).json()
    assert me["projects_completed"] == 1 and me["response_rate"] == 50 and me["response_hours"] is not None
