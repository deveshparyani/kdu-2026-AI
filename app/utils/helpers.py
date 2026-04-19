"""Small helper functions used in different modules."""

from __future__ import annotations

from pathlib import Path


def estimate_tokens(text: str) -> int:
    """
    Very rough token estimate.

    This keeps the demo simple and avoids extra tokenizer dependencies.
    A common beginner-friendly approximation is 1 token ~= 4 characters.
    """

    if not text:
        return 0
    return max(1, len(text) // 4)


def project_root_from_config_dir(config_dir: str | Path) -> Path:
    """Return the project root based on the config directory path."""

    config_path = Path(config_dir).resolve()
    return config_path.parent


def ensure_directory(path: str | Path) -> Path:
    """Return a Path object and create the directory if it is missing."""

    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory

