"""Deterministic routing based on classifier output."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.model_registry import resolve_model_for_budget


def select_route(
    config: dict[str, Any],
    classification: dict[str, str],
    budget_status: dict[str, Any],
) -> dict[str, Any]:
    """Choose the handler, model, and prompt from the YAML config."""

    category = classification["category"]
    complexity = classification["complexity"]
    response_type = classification["response_type"]

    try:
        route = deepcopy(config["routing"][category][complexity][response_type])
    except KeyError as exc:
        raise ValueError(
            "No routing rule found for "
            f"category={category}, complexity={complexity}, response_type={response_type}"
        ) from exc

    route["original_model"] = route["model"]
    route["model"] = resolve_model_for_budget(route["model"], budget_status, config)
    route["category"] = category
    route["complexity"] = complexity
    route["response_type"] = response_type
    route["human_handoff"] = bool(route.get("human_handoff", False))
    return route

