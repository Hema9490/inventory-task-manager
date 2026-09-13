from flask import Blueprint, jsonify, request

from app.db import get_conn
from app.models import DomainError, Task
from app.priority_queue import PriorityQueue

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.post("")
def create_task():
    data = request.get_json(force=True) or {}
    try:
        task = Task(
            title=data["title"],
            priority=int(data.get("priority", 3)),
            description=data.get("description", ""),
            related_item_id=data.get("related_item_id"),
        )
    except (KeyError, ValueError, DomainError) as e:
        return jsonify({"error": f"Invalid task payload: {e}"}), 400

    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO tasks (title, description, priority, status, related_item_id)
           VALUES (?, ?, ?, 'open', ?)""",
        (task.title, task.description, task.priority, task.related_item_id),
    )
    conn.commit()
    task_id = cur.lastrowid
    return jsonify(_row_to_dict(_fetch_task(conn, task_id))), 201


@tasks_bp.get("")
def list_tasks():
    conn = get_conn()
    status = request.args.get("status")
    if status:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status = ? ORDER BY priority ASC, created_at ASC",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY priority ASC, created_at ASC"
        ).fetchall()
    return jsonify([_row_to_dict(r) for r in rows])


@tasks_bp.get("/next")
def next_task():
    """Pops the highest-priority open task using the PriorityQueue structure.

    Demonstrates the heap-backed queue operating over live task rows
    rather than just a hardcoded example list.
    """
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE status = 'open'"
    ).fetchall()

    pq = PriorityQueue()
    for row in rows:
        pq.push(dict(row), row["priority"])

    if pq.is_empty():
        return jsonify({"message": "No open tasks."}), 200

    return jsonify(pq.pop())


@tasks_bp.put("/<int:task_id>/start")
def start_task(task_id):
    conn = get_conn()
    row = _fetch_task(conn, task_id)
    if not row:
        return jsonify({"error": "Task not found"}), 404
    if row["status"] != "open":
        return jsonify({"error": f"Cannot start a task with status '{row['status']}'."}), 400

    conn.execute("UPDATE tasks SET status = 'in-progress' WHERE id = ?", (task_id,))
    conn.commit()
    return jsonify(_row_to_dict(_fetch_task(conn, task_id)))


@tasks_bp.put("/<int:task_id>/complete")
def complete_task(task_id):
    conn = get_conn()
    row = _fetch_task(conn, task_id)
    if not row:
        return jsonify({"error": "Task not found"}), 404
    if row["status"] == "closed":
        return jsonify({"error": "Task is already closed."}), 400

    conn.execute(
        "UPDATE tasks SET status = 'closed', completed_at = datetime('now') WHERE id = ?",
        (task_id,),
    )
    conn.commit()
    return jsonify(_row_to_dict(_fetch_task(conn, task_id)))


def _fetch_task(conn, task_id):
    return conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()


def _row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "priority": row["priority"],
        "status": row["status"],
        "related_item_id": row["related_item_id"],
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
    }
