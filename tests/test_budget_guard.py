from app.nodes.budget_guard import budget_guard_node


def test_budget_guard_marks_pressure_before_hard_stop() -> None:
    state = {
        "config": {
            "budget": {
                "monthly_limit_usd": 500,
                "daily_query_limit": 10000,
                "enforce_budget_guard": True,
                "downgrade_on_budget_pressure": True,
            },
            "cost_control": {
                "alert_threshold_percent": 80,
                "hard_stop_threshold_percent": 100,
            },
        },
        "monthly_spend_usd": 425,
        "daily_query_count": 50,
    }

    result = budget_guard_node(state)

    assert result["budget_status"]["budget_pressure"] is True
    assert result["budget_status"]["hard_stop"] is False


def test_budget_guard_hard_stops_when_daily_limit_is_reached() -> None:
    state = {
        "config": {
            "budget": {
                "monthly_limit_usd": 500,
                "daily_query_limit": 100,
                "enforce_budget_guard": True,
                "downgrade_on_budget_pressure": True,
            },
            "cost_control": {
                "alert_threshold_percent": 80,
                "hard_stop_threshold_percent": 100,
            },
        },
        "monthly_spend_usd": 100,
        "daily_query_count": 100,
    }

    result = budget_guard_node(state)

    assert result["budget_status"]["daily_limit_reached"] is True
    assert result["budget_status"]["hard_stop"] is True

