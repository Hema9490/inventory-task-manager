from flask import Blueprint, jsonify, request

from app.db import get_conn
from app.models import DomainError, Order, RestockTask, Item

orders_bp = Blueprint("orders", __name__)


@orders_bp.post("")
def create_order():
    """Creates a sale or restock order and updates item quantity accordingly.

    A 'sale' order deducts stock; a 'restock' order adds stock. If a sale
    drops an item at/below its reorder threshold, a RestockTask is
    auto-created — this is the piece that ties inventory, tasks, and the
    priority queue together end-to-end.
    """
    data = request.get_json(force=True) or {}
    conn = get_conn()

    item_row = conn.execute(
        "SELECT * FROM items WHERE id = ?", (data.get("item_id"),)
    ).fetchone()
    if not item_row:
        return jsonify({"error": "Item not found"}), 404

    item = Item(
        id=item_row["id"], sku=item_row["sku"], name=item_row["name"],
        category=item_row["category"], quantity=item_row["quantity"],
        reorder_threshold=item_row["reorder_threshold"],
        unit_price=item_row["unit_price"],
    )

    try:
        order = Order(
            item_id=item.id,
            quantity=int(data["quantity"]),
            order_type=data.get("order_type", "sale"),
        )
        if order.order_type == "sale":
            item.deduct(order.quantity)
        else:
            item.restock(order.quantity)
    except (KeyError, ValueError, DomainError) as e:
        return jsonify({"error": str(e)}), 400

    cur = conn.execute(
        "INSERT INTO orders (item_id, quantity, order_type) VALUES (?, ?, ?)",
        (order.item_id, order.quantity, order.order_type),
    )
    conn.execute(
        "UPDATE items SET quantity = ? WHERE id = ?", (item.quantity, item.id)
    )

    auto_task_id = None
    if order.order_type == "sale" and item.is_low_stock():
        shortfall = max(item.reorder_threshold - item.quantity, 1)
        restock_task = RestockTask(item=item, shortfall=shortfall)
        task_cur = conn.execute(
            """INSERT INTO tasks (title, description, priority, status, related_item_id)
               VALUES (?, ?, ?, 'open', ?)""",
            (restock_task.title, restock_task.description, restock_task.priority, item.id),
        )
        auto_task_id = task_cur.lastrowid

    conn.commit()
    order.id = cur.lastrowid

    response = {
        "order": {
            "id": order.id,
            "item_id": order.item_id,
            "quantity": order.quantity,
            "order_type": order.order_type,
        },
        "item_quantity_after": item.quantity,
        "auto_generated_restock_task_id": auto_task_id,
    }
    return jsonify(response), 201


@orders_bp.get("")
def list_orders():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM orders ORDER BY created_at DESC"
    ).fetchall()
    return jsonify([
        {
            "id": r["id"], "item_id": r["item_id"], "quantity": r["quantity"],
            "order_type": r["order_type"], "created_at": r["created_at"],
        }
        for r in rows
    ])
