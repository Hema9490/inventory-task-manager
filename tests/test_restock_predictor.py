from app.ml.restock_predictor import predict_restock


def test_no_history_returns_low_confidence_unknown_forecast():
    result = predict_restock(current_quantity=10, usage_history=[])
    assert result.confidence == "low"
    assert result.predicted_days_until_stockout == float("inf")
    assert "no sales history" in result.recommendation.lower()


def test_single_data_point_uses_that_value_directly():
    result = predict_restock(current_quantity=20, usage_history=[("2026-09-01", 5)])
    assert result.avg_daily_usage == 5.0
    assert result.predicted_days_until_stockout == 4.0


def test_steady_usage_produces_reasonable_forecast():
    history = [(f"2026-09-0{d}", 4) for d in range(1, 6)]  # 4 units/day, 5 days
    result = predict_restock(current_quantity=40, usage_history=history)
    assert 3.5 <= result.avg_daily_usage <= 4.5
    assert result.confidence == "medium"


def test_urgent_recommendation_when_stockout_imminent():
    history = [("2026-09-01", 10), ("2026-09-02", 10)]
    result = predict_restock(current_quantity=15, usage_history=history)
    assert result.predicted_days_until_stockout <= 3
    assert "urgent" in result.recommendation.lower()


def test_confidence_increases_with_more_history():
    short_history = [("2026-09-01", 3), ("2026-09-02", 3)]
    long_history = [(f"2026-09-{str(d).zfill(2)}", 3) for d in range(1, 10)]

    short_result = predict_restock(current_quantity=50, usage_history=short_history)
    long_result = predict_restock(current_quantity=50, usage_history=long_history)

    assert short_result.confidence == "low"
    assert long_result.confidence == "high"
