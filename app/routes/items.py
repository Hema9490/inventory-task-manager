from flask import Blueprint, jsonify, request

from app.db import get_conn
from app.models import DomainError, Item
from app.search_sort import binary_search_by_sku, merge_sort_items_by_quantity

items_bp = Blueprint("items", __name__)


def _row_to_item(row) -> Item:
    return Item(
        id=row["id"],
        sku=row["sku"],
        name=row["name"],
        category=row["category"],
        quantity=row["quantity"],
        reorder_threshold=row["reorder_threshold"],
        unit_price=row["unit_price"],
    )


@items_bp.post("")
def create_item():
    data = request.get_json(force=True) or {}
    try:
        item = Item(
            sku=data["sku"],
            name=data["name"],
            category=data.get("category", "general"),
            quantity=int(data.get("quantity", 0)),
            reorder_threshold=int(data.get("reorder_threshold", 5)),
            unit_price=float(data.get("unit_price", 0.0)),
        )
    except (KeyError, ValueError) as e:
        return jsonify({"error": f"Invalid item payload: {e}"}), 400

    conn = get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO items (sku, name, category, quantity, reorder_threshold, unit_price)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (item.sku, item.name, item.category, item.quantity,
             item.reorder_threshold, item.unit_price),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Could not create item: {e}"}), 400

    item.id = cur.lastrowid
    return jsonify(_item_to_dict(item)), 201


@items_bp.get("")
def list_items():
    """List items, optionally sorted by quantity ascending (?sort=quantity)."""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM items ORDER BY sku ASC").fetchall()
    items = [_row_to_item(r) for r in rows]

    if request.args.get("sort") == "quantity":
        items = merge_sort_items_by_quantity(items)

    return jsonify([_item_to_dict(i) for i in items])


@items_bp.get("/lookup/<sku>")
def lookup_by_sku(sku):
    """Binary-search lookup by SKU — items are fetched pre-sorted by sku."""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM items ORDER BY sku ASC").fetchall()
    items = [_row_to_item(r) for r in rows]
    found = binary_search_by_sku(items, sku)
    if not found:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(_item_to_dict(found))


@items_bp.get("/<int:item_id>")
def get_item(item_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(_item_to_dict(_row_to_item(row)))


@items_bp.put("/<int:item_id>")
def update_item(item_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        return jsonify({"error": "Item not found"}), 404

    data = request.get_json(force=True) or {}
    item = _row_to_item(row)

    try:
        if "quantity" in data:
            item.quantity = int(data["quantity"])
        if "reorder_threshold" in data:
            item.reorder_threshold = int(data["reorder_threshold"])
        if "unit_price" in data:
            item.unit_price = float(data["unit_price"])
        if "name" in data:
            item.name = data["name"]
        if "category" in data:
            item.category = data["category"]
    except (ValueError, DomainError) as e:
        return jsonify({"error": str(e)}), 400

    conn.execute(
        """UPDATE items SET name=?, category=?, quantity=?, reorder_threshold=?, unit_price=?
           WHERE id=?""",
        (item.name, item.category, item.quantity, item.reorder_threshold,
         item.unit_price, item_id),
    )
    conn.commit()
    return jsonify(_item_to_dict(item))


@items_bp.delete("/<int:item_id>")
def delete_item(item_id):
    conn = get_conn()
    row = conn.execute("SELECT id FROM items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        return jsonify({"error": "Item not found"}), 404
    conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    return "", 204


def _item_to_dict(item: Item) -> dict:
    return {
        "id": item.id,
        "sku": item.sku,
        "name": item.name,
        "category": item.category,
        "quantity": item.quantity,
        "reorder_threshold": item.reorder_threshold,
        "unit_price": item.unit_price,
        "is_low_stock": item.is_low_stock(),
    }
