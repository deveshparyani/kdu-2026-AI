"""Load YAML configuration into state."""

from __future__ import annotations

from app.services.config_loader import load_full_config
from app.state import FixItState


def load_config_node(state: FixItState) -> dict:
    config = load_full_config(state.get("config_dir", "config"))
    return {"config": config}

