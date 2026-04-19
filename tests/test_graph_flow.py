from app.graph import build_graph
from app.state import build_initial_state


def test_graph_runs_end_to_end_for_complaint_flow() -> None:
    graph = build_graph()
    state = build_initial_state(
        query="My plumber didn't show up and I want a refund",
        config_dir="config",
        monthly_spend_usd=0.0,
        daily_query_count=0,
    )

    result = graph.invoke(state)

    assert result["classification"]["category"] == "complaint"
    assert result["route"]["prompt"] == "complaint.complex"
    assert result["route"]["model"] == "premium"
    assert result["cost"]["human_handoff"] is True
    assert "human support review" in result["response_text"]


def test_graph_downgrades_route_when_budget_is_under_pressure() -> None:
    graph = build_graph()
    state = build_initial_state(
        query="My plumber didn't show up and I want a refund",
        config_dir="config",
        monthly_spend_usd=450.0,
        daily_query_count=0,
    )

    result = graph.invoke(state)

    assert result["classification"]["category"] == "complaint"
    assert result["route"]["original_model"] == "premium"
    assert result["route"]["model"] == "standard"

