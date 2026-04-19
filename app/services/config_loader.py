"""Read and validate the YAML configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.utils.validators import require_keys, validate_routing_references


CONFIG_FILES = {
    "config": "config.yaml",
    "models": "models.yaml",
    "routing": "routing.yaml",
    "feature_flags": "feature_flags.yaml",
    "budget": "budget.yaml",
}


def _read_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML object: {path}")

    return data


def load_full_config(config_dir: str = "config") -> dict[str, Any]:
    """Load all config files into one dictionary."""

    base_dir = Path(config_dir).resolve()

    merged: dict[str, Any] = {}
    for file_name in CONFIG_FILES.values():
        current = _read_yaml_file(base_dir / file_name)
        merged.update(current)

    validate_config(merged)
    return merged


def validate_config(config: dict[str, Any]) -> None:
    """Validate the required top-level sections and references."""

    require_keys(config, ["app", "models", "routing", "prompts"], "root")
    require_keys(config, ["budget", "cost_control"], "budget")
    require_keys(config, ["feature_flags"], "feature_flags")
    require_keys(config, ["fallback", "orchestrator", "logging"], "config")
    validate_routing_references(config)

