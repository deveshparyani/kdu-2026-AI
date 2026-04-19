"""Helpers for reading model configuration."""

from __future__ import annotations

from typing import Any


def get_model_config(config: dict[str, Any], model_key: str) -> dict[str, Any]:
    """Return a model configuration by its logical name."""

    try:
        return config["models"][model_key]
    except KeyError as exc:
        raise ValueError(f"Unknown model key: {model_key}") from exc


def downgrade_model(model_key: str) -> str:
    """Move to a cheaper model during budget pressure."""

    if model_key == "premium":
        return "standard"
    if model_key == "standard":
        return "cheap"
    return "cheap"


def resolve_model_for_budget(
    configured_model: str,
    budget_status: dict[str, Any],
    config: dict[str, Any],
) -> str:
    """Pick a final model after budget rules are applied."""

    if budget_status.get("hard_stop"):
        return config["fallback"]["on_budget_exceeded"]

    if budget_status.get("budget_pressure") and config["budget"]["downgrade_on_budget_pressure"]:
        return downgrade_model(configured_model)

    return configured_model

