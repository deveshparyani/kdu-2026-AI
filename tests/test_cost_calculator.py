from app.services.cost_calculator import calculate_query_cost, evaluate_budget_status


def test_calculate_query_cost() -> None:
    model_config = {
        "input_cost_per_1k_tokens": 0.002,
        "output_cost_per_1k_tokens": 0.008,
    }
    result = calculate_query_cost(model_config, input_tokens=120, output_tokens=180)

    assert result["input_cost_usd"] == 0.00024
    assert result["output_cost_usd"] == 0.00144
    assert result["total_cost_usd"] == 0.00168


def test_evaluate_budget_status() -> None:
    result = evaluate_budget_status(
        monthly_limit_usd=500,
        current_month_spend_usd=450,
        alert_threshold_percent=80,
        hard_stop_threshold_percent=100,
    )

    assert result["usage_percent"] == 90.0
    assert result["budget_pressure"] is True
    assert result["hard_stop"] is False

