"""Budget guard node."""

from __future__ import annotations

from app.services.cost_calculator import evaluate_budget_status
from app.state import FixItState


def budget_guard_node(state: FixItState) -> dict:
    config = state["config"]
    budget = config["budget"]
    cost_control = config["cost_control"]

    budget_status = evaluate_budget_status(
        monthly_limit_usd=budget["monthly_limit_usd"],
        current_month_spend_usd=state.get("monthly_spend_usd", 0.0),
        alert_threshold_percent=cost_control["alert_threshold_percent"],
        hard_stop_threshold_percent=cost_control["hard_stop_threshold_percent"],
    )

    budget_status["daily_limit_reached"] = (
        state.get("daily_query_count", 0) >= budget["daily_query_limit"]
    )
    budget_status["budget_guard_enabled"] = budget["enforce_budget_guard"]
    if budget_status["budget_guard_enabled"] and budget_status["daily_limit_reached"]:
        budget_status["hard_stop"] = True

    return {"budget_status": budget_status}
