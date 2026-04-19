"""Workflow graph for the FixIt support system."""

from __future__ import annotations

from typing import Any

from app.nodes.booking_handler import booking_handler_node
from app.nodes.budget_guard import budget_guard_node
from app.nodes.complaint_handler import complaint_handler_node
from app.nodes.cost_tracker import cost_tracker_node
from app.nodes.faq_handler import faq_handler_node
from app.nodes.load_config import load_config_node
from app.nodes.orchestrator_classifier import orchestrator_classifier_node
from app.state import FixItState

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:  # pragma: no cover - fallback used only if langgraph is missing
    END = "END"
    START = "START"
    StateGraph = None


def _select_category_node(state: FixItState) -> str:
    return state["classification"]["category"]


class LocalGraphRunner:
    """Small fallback runner when LangGraph is not installed."""

    def invoke(self, state: FixItState) -> FixItState:
        state.update(load_config_node(state))
        state.update(budget_guard_node(state))
        state.update(orchestrator_classifier_node(state))

        category = state["classification"]["category"]
        if category == "FAQ":
            state.update(faq_handler_node(state))
        elif category == "booking":
            state.update(booking_handler_node(state))
        elif category == "complaint":
            state.update(complaint_handler_node(state))
        else:
            raise ValueError(f"Unsupported category: {category}")

        state.update(cost_tracker_node(state))
        return state


def build_graph() -> Any:
    """Build a LangGraph workflow or a local fallback."""

    if StateGraph is None:
        return LocalGraphRunner()

    workflow = StateGraph(FixItState)
    workflow.add_node("load_config", load_config_node)
    workflow.add_node("budget_guard", budget_guard_node)
    workflow.add_node("orchestrator_classifier", orchestrator_classifier_node)
    workflow.add_node("FAQ", faq_handler_node)
    workflow.add_node("booking", booking_handler_node)
    workflow.add_node("complaint", complaint_handler_node)
    workflow.add_node("cost_tracker", cost_tracker_node)

    workflow.add_edge(START, "load_config")
    workflow.add_edge("load_config", "budget_guard")
    workflow.add_edge("budget_guard", "orchestrator_classifier")
    workflow.add_conditional_edges(
        "orchestrator_classifier",
        _select_category_node,
        {
            "FAQ": "FAQ",
            "booking": "booking",
            "complaint": "complaint",
        },
    )
    workflow.add_edge("FAQ", "cost_tracker")
    workflow.add_edge("booking", "cost_tracker")
    workflow.add_edge("complaint", "cost_tracker")
    workflow.add_edge("cost_tracker", END)

    return workflow.compile()

