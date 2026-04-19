"""FAQ branch node."""

from __future__ import annotations

from app.nodes.shared_handler import run_category_handler
from app.state import FixItState


def faq_handler_node(state: FixItState) -> dict:
    return run_category_handler(state, category="FAQ")

