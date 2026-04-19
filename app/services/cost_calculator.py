"""Cost estimation helpers."""

from __future__ import annotations


def calculate_query_cost(
    model_config: dict[str, float],
    input_tokens: int,
    output_tokens: int,
) -> dict[str, float]:
    """Calculate the estimated cost for one LLM request."""

    input_cost = (input_tokens / 1000) * model_config["input_cost_per_1k_tokens"]
    output_cost = (output_tokens / 1000) * model_config["output_cost_per_1k_tokens"]
    total_cost = input_cost + output_cost

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost_usd": round(input_cost, 8),
        "output_cost_usd": round(output_cost, 8),
        "total_cost_usd": round(total_cost, 8),
    }


def evaluate_budget_status(
    monthly_limit_usd: float,
    current_month_spend_usd: float,
    alert_threshold_percent: float,
    hard_stop_threshold_percent: float,
) -> dict[str, float | bool]:
    """Return budget health flags used by the budget guard."""

    if monthly_limit_usd <= 0:
        raise ValueError("monthly_limit_usd must be greater than zero")

    usage_percent = (current_month_spend_usd / monthly_limit_usd) * 100
    budget_pressure = usage_percent >= alert_threshold_percent
    hard_stop = usage_percent >= hard_stop_threshold_percent

    return {
        "usage_percent": round(usage_percent, 2),
        "budget_pressure": budget_pressure,
        "hard_stop": hard_stop,
    }

