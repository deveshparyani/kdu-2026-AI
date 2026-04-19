"""Simple logger setup."""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """Create a console logger with a friendly default format."""

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger

