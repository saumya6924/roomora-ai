from app.core.enums import Role


def approved_product(client, seller, admin, **overrides):
    body = {"name": "Teak Sofa", "price": 20000, "stock": 3, "category": "Sofa", **overrides}
    r = client.post("/products", headers=seller["headers"], json=body)
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    client.patch(f"/products/{pid}/status", headers=admin["headers"], json={"status": "approved"})
    return pid


def test_seller_flow_and_visibility(client, accounts):
    user = accounts.make("Asha", "asha@gmail.com")
    seller = accounts.make("Sam", "sam@gmail.com", Role.SELLER)
    admin = accounts.make("Root", "root@gmail.com", Role.ADMIN)

    assert (
        client.post(
            "/products", headers=user["headers"], json={"name": "Hack Sofa", "price": 100}
        ).status_code
        == 403
    )

    r = client.post(
        "/products",
        headers=seller["headers"],
        json={"name": "Teak Sofa", "price": 20000, "stock": 3, "category": "Sofa"},
    )
    assert r.status_code == 201 and r.json()["status"] == "pending"
    pid = r.json()["id"]

    assert client.get("/products").json() == []  # pending products are invisible
    assert client.get(f"/products/{pid}").status_code == 404
    assert (
        client.patch(
            f"/products/{pid}/status", headers=seller["headers"], json={"status": "approved"}
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/products/{pid}/status", headers=admin["headers"], json={"status": "bogus"}
        ).status_code
        == 400
    )
    assert (
        client.patch(
            f"/products/{pid}/status", headers=admin["headers"], json={"status": "approved"}
        ).status_code
        == 200
    )

    assert len(client.get("/products?search=teak").json()) == 1
    assert client.get("/products?max_price=100").json() == []
    assert (
        client.get("/products/mine", headers=seller["headers"]).json()[0]["id"] == pid
    )  # /mine is not read as an id
    assert [p["id"] for p in client.get("/products/pending", headers=admin["headers"]).json()] == []


def test_price_is_a_number_in_json(client, accounts):
    seller = accounts.make("Sam", "sam@gmail.com", Role.SELLER)
    r = client.post("/products", headers=seller["headers"], json={"name": "Lamp", "price": 1999.5})
    assert r.json()["price"] == 1999.5 and isinstance(r.json()["price"], float)


def test_full_product_form_round_trip(client, accounts):
    seller = accounts.make("Sam", "sam@gmail.com", Role.SELLER)
    body = {
        "name": "Modern Boucle Sofa",
        "category": "Sofa",
        "price": 42999,
        "mrp": 49999,
        "gst_percent": 12,
        "discount_percent": 10,
        "sku": "UL-SOF-001",
        "stock": 50,
        "low_stock_threshold": 5,
        "warehouse": "Ahmedabad Warehouse",
        "length_cm": 210,
        "width_cm": 90,
        "height_cm": 85,
        "weight_kg": 45,
        "material": "Fabric",
        "color": "Cream Beige",
        "finish": "Matte",
        "seating_capacity": "3 Seater",
        "key_features": "Stain resistant",
        "delivery_time": "5 - 7 Business Days",
        "shipping_charge": 999,
        "assembly": "Yes - Free",
        "installation_charge": 0,
        "delivery_areas": "Ahmedabad, Mumbai",
        "return_period": "7 Days",
        "warranty": "1 Year",
        "return_policy": "Damaged items replaced.",
        "image_urls": ["https://example.com/a.jpg", "https://example.com/b.jpg"],
    }
    r = client.post("/products", headers=seller["headers"], json=body)
    assert r.status_code == 201, r.text
    product = r.json()
    for field in ("sku", "material", "warehouse", "warranty", "delivery_time", "assembly"):
        assert product[field] == body[field]
    assert product["length_cm"] == 210 and product["weight_kg"] == 45
    assert product["image_url"] == "https://example.com/a.jpg"
    assert [i["url"] for i in product["images"]] == body["image_urls"]

    # a second product with the same SKU from the same seller is rejected
    assert (
        client.post("/products", headers=seller["headers"], json={**body, "name": "Copy"}).status_code == 400
    )

    # partial update keeps everything else
    r = client.put(
        f"/products/{product['id']}", headers=seller["headers"], json={"stock": 7, "color": "Grey"}
    )
    assert r.status_code == 200 and r.json()["stock"] == 7 and r.json()["color"] == "Grey"
    assert r.json()["sku"] == "UL-SOF-001"


def test_validation_and_ownership(client, accounts):
    seller = accounts.make("Sam", "sam@gmail.com", Role.SELLER)
    other = accounts.make("Olly", "olly@gmail.com", Role.SELLER)
    assert (
        client.post("/products", headers=seller["headers"], json={"name": "Free", "price": 0}).status_code
        == 422
    )
    assert (
        client.post(
            "/products", headers=seller["headers"], json={"name": "Neg", "price": 5, "stock": -1}
        ).status_code
        == 422
    )
    too_many = {"name": "Pics", "price": 5, "image_urls": ["u"] * 6}
    assert client.post("/products", headers=seller["headers"], json=too_many).status_code == 422

    pid = client.post("/products", headers=seller["headers"], json={"name": "Chair", "price": 500}).json()[
        "id"
    ]
    assert client.put(f"/products/{pid}", headers=other["headers"], json={"stock": 1}).status_code == 403
    assert client.delete(f"/products/{pid}", headers=other["headers"]).status_code == 403
    assert client.delete(f"/products/{pid}", headers=seller["headers"]).status_code == 200
