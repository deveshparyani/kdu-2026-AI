"""Validation helpers for YAML configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def require_keys(data: dict[str, Any], keys: list[str], section_name: str) -> None:
    """Raise a clear error if required keys are missing."""

    missing = [key for key in keys if key not in data]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required keys in '{section_name}': {joined}")


def validate_routing_references(config: dict[str, Any]) -> None:
    """Make sure routing refers to real models and prompt mappings."""

    models = set(config["models"].keys())
    prompts = config["prompts"]

    for category, complexity_map in config["routing"].items():
        for complexity_map_entry in complexity_map.values():
            for response_type, route in complexity_map_entry.items():
                model_name = route["model"]
                prompt_reference = route["prompt"]

                if model_name not in models:
                    raise ValueError(
                        "Routing uses unknown model "
                        f"'{model_name}' in category '{category}' and response type '{response_type}'."
                    )

                prompt_category, prompt_level = prompt_reference.split(".")
                if prompt_category not in prompts:
                    raise ValueError(
                        f"Prompt category '{prompt_category}' is missing from config."
                    )
                if prompt_level not in prompts[prompt_category]:
                    raise ValueError(
                        f"Prompt level '{prompt_reference}' is missing from config."
                    )


def validate_prompt_file(path: Path) -> None:
    """Raise a friendly error when a prompt file is missing."""

    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
