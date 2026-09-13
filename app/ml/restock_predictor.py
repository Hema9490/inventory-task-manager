"""
AI/ML module: predicts days-until-stockout from recent sales history
using a simple linear regression over daily units sold.

Deliberately lightweight (no external model files, trains on request
from the item's own order history) so it's easy to explain end-to-end
in an interview: this is a transparent, from-scratch fit, not a
black-box import.
"""

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from sklearn.linear_model import LinearRegression


@dataclass
class RestockPrediction:
    item_id: int
    current_quantity: int
    avg_daily_usage: float
    predicted_days_until_stockout: float
    confidence: str  # "low" | "medium" | "high" — based on history length
    recommendation: str


def _confidence_from_sample_size(n: int) -> str:
    if n < 3:
        return "low"
    if n < 7:
        return "medium"
    return "high"


def predict_restock(
    current_quantity: int,
    usage_history: List[Tuple[str, int]],
) -> RestockPrediction:
    """
    usage_history: list of (date_str, units_sold) pairs, ascending by date,
    typically the result of db.ITEM_USAGE_HISTORY_QUERY.

    Fits units_sold ~ day_index with linear regression to get a trend-aware
    average daily usage rate, then projects days until stock hits zero.
    """
    if not usage_history:
        return RestockPrediction(
            item_id=-1,
            current_quantity=current_quantity,
            avg_daily_usage=0.0,
            predicted_days_until_stockout=float("inf"),
            confidence="low",
            recommendation="No sales history yet — cannot forecast usage.",
        )

    days = np.array([[i] for i in range(len(usage_history))])
    units = np.array([u for _, u in usage_history])

    if len(usage_history) == 1:
        avg_daily_usage = float(units[0])
    else:
        model = LinearRegression()
        model.fit(days, units)
        # Use the fitted mean rate rather than the raw slope, so a single
        # noisy day can't produce a negative or wildly skewed usage rate.
        predicted = model.predict(days)
        avg_daily_usage = float(max(np.mean(predicted), 0.01))

    days_until_stockout = current_quantity / avg_daily_usage if avg_daily_usage > 0 else float("inf")

    if days_until_stockout <= 3:
        recommendation = "Urgent: restock within the next few days."
    elif days_until_stockout <= 7:
        recommendation = "Plan a restock within the next week."
    else:
        recommendation = "Stock level is healthy for now."

    return RestockPrediction(
        item_id=-1,
        current_quantity=current_quantity,
        avg_daily_usage=round(avg_daily_usage, 2),
        predicted_days_until_stockout=round(days_until_stockout, 1) if days_until_stockout != float("inf") else float("inf"),
        confidence=_confidence_from_sample_size(len(usage_history)),
        recommendation=recommendation,
    )
