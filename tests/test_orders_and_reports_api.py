def _create_item(client, **overrides):
    payload = {
        "sku": "SKU001", "name": "Widget", "category": "tools",
        "quantity": 10, "reorder_threshold": 5, "unit_price": 2.5,
    }
    payload.update(overrides)
    return client.post("/api/items", json=payload).get_json()


def test_sale_order_deducts_stock(client):
    item = _create_item(client)
    resp = client.post("/api/orders", json={
        "item_id": item["id"], "quantity": 3, "order_type": "sale",
    })
    assert resp.status_code == 201
    assert resp.get_json()["item_quantity_after"] == 7


def test_sale_order_auto_creates_restock_task_when_low(client):
    item = _create_item(client, quantity=6, reorder_threshold=5)
    resp = client.post("/api/orders", json={
        "item_id": item["id"], "quantity": 2, "order_type": "sale",
    })
    data = resp.get_json()
    assert data["item_quantity_after"] == 4
    assert data["auto_generated_restock_task_id"] is not None

    tasks = client.get("/api/tasks").get_json()
    assert any(t["related_item_id"] == item["id"] for t in tasks)


def test_sale_order_rejects_overselling(client):
    item = _create_item(client, quantity=2)
    resp = client.post("/api/orders", json={
        "item_id": item["id"], "quantity": 10, "order_type": "sale",
    })
    assert resp.status_code == 400


def test_restock_order_increases_stock(client):
    item = _create_item(client, quantity=2)
    resp = client.post("/api/orders", json={
        "item_id": item["id"], "quantity": 20, "order_type": "restock",
    })
    assert resp.get_json()["item_quantity_after"] == 22


def test_order_for_missing_item(client):
    resp = client.post("/api/orders", json={
        "item_id": 999, "quantity": 1, "order_type": "sale",
    })
    assert resp.status_code == 404


def test_low_stock_report(client):
    _create_item(client, sku="LOW", quantity=1, reorder_threshold=5)
    _create_item(client, sku="OK", quantity=50, reorder_threshold=5)
    resp = client.get("/api/reports/low-stock")
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["sku"] == "LOW"


def test_restock_prediction_no_history(client):
    item = _create_item(client)
    resp = client.get(f"/api/reports/restock-prediction/{item['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["confidence"] == "low"


def test_restock_prediction_with_sales_history(client):
    item = _create_item(client, quantity=50)
    for _ in range(3):
        client.post("/api/orders", json={
            "item_id": item["id"], "quantity": 5, "order_type": "sale",
        })
    resp = client.get(f"/api/reports/restock-prediction/{item['id']}")
    data = resp.get_json()
    assert data["current_quantity"] == 35
    assert "recommendation" in data


def test_restock_prediction_item_not_found(client):
    resp = client.get("/api/reports/restock-prediction/999")
    assert resp.status_code == 404


def test_task_load_report(client):
    client.post("/api/tasks", json={"title": "A", "priority": 1})
    client.post("/api/tasks", json={"title": "B", "priority": 2})
    resp = client.get("/api/reports/task-load")
    assert resp.get_json()["open"] == 2
