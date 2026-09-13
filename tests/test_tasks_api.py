def _create_task(client, **overrides):
    payload = {"title": "Fix bug", "priority": 3, "description": "details"}
    payload.update(overrides)
    return client.post("/api/tasks", json=payload)


def test_create_task(client):
    resp = _create_task(client)
    assert resp.status_code == 201
    assert resp.get_json()["status"] == "open"


def test_create_task_invalid_priority(client):
    resp = _create_task(client, priority=9)
    assert resp.status_code == 400


def test_list_tasks(client):
    _create_task(client, title="A")
    _create_task(client, title="B")
    resp = client.get("/api/tasks")
    assert len(resp.get_json()) == 2


def test_list_tasks_filtered_by_status(client):
    created = _create_task(client).get_json()
    client.put(f"/api/tasks/{created['id']}/start")
    resp = client.get("/api/tasks?status=in-progress")
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["status"] == "in-progress"


def test_next_task_returns_highest_priority(client):
    _create_task(client, title="Low", priority=5)
    _create_task(client, title="Urgent", priority=1)
    resp = client.get("/api/tasks/next")
    assert resp.get_json()["title"] == "Urgent"


def test_next_task_when_empty(client):
    resp = client.get("/api/tasks/next")
    assert "message" in resp.get_json()


def test_start_then_complete_task(client):
    created = _create_task(client).get_json()
    task_id = created["id"]

    start_resp = client.put(f"/api/tasks/{task_id}/start")
    assert start_resp.get_json()["status"] == "in-progress"

    complete_resp = client.put(f"/api/tasks/{task_id}/complete")
    assert complete_resp.get_json()["status"] == "closed"
    assert complete_resp.get_json()["completed_at"] is not None


def test_cannot_start_twice(client):
    created = _create_task(client).get_json()
    task_id = created["id"]
    client.put(f"/api/tasks/{task_id}/start")
    resp = client.put(f"/api/tasks/{task_id}/start")
    assert resp.status_code == 400


def test_task_not_found(client):
    resp = client.put("/api/tasks/999/start")
    assert resp.status_code == 404
