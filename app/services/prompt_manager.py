"""Load prompt templates and fill variables."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.utils.helpers import project_root_from_config_dir
from app.utils.validators import validate_prompt_file


def get_prompt_definition(
    config: dict[str, Any],
    prompt_reference: str,
) -> dict[str, Any]:
    """Find prompt metadata from a reference like 'faq.simple'."""

    prompt_category, prompt_level = prompt_reference.split(".")
    return config["prompts"][prompt_category][prompt_level]


def load_prompt_file(
    config: dict[str, Any],
    config_dir: str,
    prompt_reference: str,
) -> dict[str, Any]:
    """Load the YAML file for the chosen prompt."""

    prompt_definition = get_prompt_definition(config, prompt_reference)
    template_id = prompt_definition["template_id"]

    prompt_category, _ = prompt_reference.split(".")
    project_root = project_root_from_config_dir(config_dir)
    prompt_path = project_root / "prompts" / prompt_category / f"{template_id}.yaml"

    validate_prompt_file(prompt_path)

    with prompt_path.open("r", encoding="utf-8") as handle:
        file_data = yaml.safe_load(handle) or {}

    return {
        "reference": prompt_reference,
        "version": prompt_definition["version"],
        "template_id": template_id,
        "file_path": str(prompt_path),
        "content": file_data,
    }


def render_prompt(prompt_data: dict[str, Any], variables: dict[str, Any]) -> dict[str, str]:
    """Substitute variables into the prompt template."""

    content = prompt_data["content"]
    system_message = content["system_message"].format(**variables)
    user_message = content["user_message"].format(**variables)
    return {"system_message": system_message, "user_message": user_message}

