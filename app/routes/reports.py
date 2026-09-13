from flask import Blueprint, jsonify

from app.db import (
    get_conn,
    LOW_STOCK_QUERY,
    SALES_TREND_QUERY,
    ITEM_USAGE_HISTORY_QUERY,
    TASK_LOAD_BY_STATUS_QUERY,
)
from app.ml.restock_predictor import predict_restock

reports_bp = Blueprint("reports", __name__)


@reports_bp.get("/low-stock")
def low_stock_report():
    conn = get_conn()
    rows = conn.execute(LOW_STOCK_QUERY).fetchall()
    return jsonify([dict(r) for r in rows])


@reports_bp.get("/sales-trend")
def sales_trend_report():
    conn = get_conn()
    rows = conn.execute(SALES_TREND_QUERY).fetchall()
    return jsonify([dict(r) for r in rows])


@reports_bp.get("/task-load")
def task_load_report():
    conn = get_conn()
    rows = conn.execute(TASK_LOAD_BY_STATUS_QUERY).fetchall()
    return jsonify({r["status"]: r["count"] for r in rows})


@reports_bp.get("/restock-prediction/<int:item_id>")
def restock_prediction(item_id):
    """AI/ML endpoint: forecasts days-until-stockout for a given item."""
    conn = get_conn()
    item_row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not item_row:
        return jsonify({"error": "Item not found"}), 404

    history_rows = conn.execute(ITEM_USAGE_HISTORY_QUERY, (item_id,)).fetchall()
    history = [(r["order_date"], r["units"]) for r in history_rows]

    prediction = predict_restock(
        current_quantity=item_row["quantity"],
        usage_history=history,
    )
    prediction.item_id = item_id

    return jsonify({
        "item_id": prediction.item_id,
        "current_quantity": prediction.current_quantity,
        "avg_daily_usage": prediction.avg_daily_usage,
        "predicted_days_until_stockout": prediction.predicted_days_until_stockout
            if prediction.predicted_days_until_stockout != float("inf") else None,
        "confidence": prediction.confidence,
        "recommendation": prediction.recommendation,
    })
