"""Shared state objects used across the FixIt workflow."""

from __future__ import annotations

from typing import Any, Dict, TypedDict


class FixItState(TypedDict, total=False):
    """Simple workflow state passed between nodes."""

    query: str
    config_dir: str
    config: Dict[str, Any]
    budget_status: Dict[str, Any]
    classification: Dict[str, str]
    route: Dict[str, Any]
    prompt: Dict[str, Any]
    llm_result: Dict[str, Any]
    response_text: str
    cost: Dict[str, Any]
    errors: list[str]
    monthly_spend_usd: float
    daily_query_count: int


def build_initial_state(
    query: str,
    config_dir: str = "config",
    monthly_spend_usd: float = 0.0,
    daily_query_count: int = 0,
) -> FixItState:
    """Create a beginner-friendly initial state dictionary."""

    return FixItState(
        query=query,
        config_dir=config_dir,
        monthly_spend_usd=monthly_spend_usd,
        daily_query_count=daily_query_count,
        errors=[],
    )

