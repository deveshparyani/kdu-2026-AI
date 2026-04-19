from app.services.config_loader import load_full_config
from app.services.router import select_route


def test_router_selects_expected_faq_route() -> None:
    config = load_full_config("config")
    route = select_route(
        config=config,
        classification={
            "category": "FAQ",
            "complexity": "low",
            "response_type": "simple",
        },
        budget_status={"budget_pressure": False, "hard_stop": False},
    )

    assert route["handler"] == "faq_handler"
    assert route["model"] == "cheap"
    assert route["prompt"] == "faq.simple"


def test_router_downgrades_under_budget_pressure() -> None:
    config = load_full_config("config")
    route = select_route(
        config=config,
        classification={
            "category": "complaint",
            "complexity": "high",
            "response_type": "complex",
        },
        budget_status={"budget_pressure": True, "hard_stop": False},
    )

    assert route["original_model"] == "premium"
    assert route["model"] == "standard"
    assert route["human_handoff"] is True


def test_router_uses_fallback_after_hard_stop() -> None:
    config = load_full_config("config")
    route = select_route(
        config=config,
        classification={
            "category": "complaint",
            "complexity": "high",
            "response_type": "complex",
        },
        budget_status={"budget_pressure": True, "hard_stop": True},
    )

    assert route["model"] == "cheap"

