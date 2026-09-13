def _create_item(client, **overrides):
    payload = {
        "sku": "SKU001",
        "name": "Widget",
        "category": "tools",
        "quantity": 10,
        "reorder_threshold": 5,
        "unit_price": 2.5,
    }
    payload.update(overrides)
    return client.post("/api/items", json=payload)


def test_create_item(client):
    resp = _create_item(client)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["sku"] == "SKU001"
    assert data["is_low_stock"] is False


def test_create_item_missing_required_field(client):
    resp = client.post("/api/items", json={"name": "No SKU"})
    assert resp.status_code == 400


def test_create_item_duplicate_sku_rejected(client):
    _create_item(client)
    resp = _create_item(client)
    assert resp.status_code == 400


def test_list_items(client):
    _create_item(client, sku="SKU001")
    _create_item(client, sku="SKU002")
    resp = client.get("/api/items")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2


def test_list_items_sorted_by_quantity(client):
    _create_item(client, sku="SKU001", quantity=50)
    _create_item(client, sku="SKU002", quantity=5)
    resp = client.get("/api/items?sort=quantity")
    data = resp.get_json()
    assert data[0]["sku"] == "SKU002"
    assert data[1]["sku"] == "SKU001"


def test_get_item_by_id(client):
    created = _create_item(client).get_json()
    resp = client.get(f"/api/items/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["sku"] == "SKU001"


def test_get_item_not_found(client):
    resp = client.get("/api/items/999")
    assert resp.status_code == 404


def test_lookup_by_sku(client):
    _create_item(client, sku="SKU001")
    _create_item(client, sku="SKU002")
    resp = client.get("/api/items/lookup/SKU002")
    assert resp.status_code == 200
    assert resp.get_json()["sku"] == "SKU002"


def test_lookup_by_sku_not_found(client):
    resp = client.get("/api/items/lookup/NOPE")
    assert resp.status_code == 404


def test_update_item_quantity(client):
    created = _create_item(client).get_json()
    resp = client.put(f"/api/items/{created['id']}", json={"quantity": 99})
    assert resp.status_code == 200
    assert resp.get_json()["quantity"] == 99


def test_delete_item(client):
    created = _create_item(client).get_json()
    resp = client.delete(f"/api/items/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/api/items/{created['id']}").status_code == 404
