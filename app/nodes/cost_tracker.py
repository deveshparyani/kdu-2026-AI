"""Final node that records cost details."""

from __future__ import annotations

from app.services.cost_calculator import calculate_query_cost
from app.services.model_registry import get_model_config
from app.state import FixItState


def cost_tracker_node(state: FixItState) -> dict:
    route = state["route"]
    model_config = get_model_config(state["config"], route["model"])
    usage = state["llm_result"]["usage"]

    cost = calculate_query_cost(
        model_config=model_config,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
    )
    cost["model_name"] = route["model"]
    cost["prompt_version"] = state["prompt"]["version"]
    cost["prompt_template_id"] = state["prompt"]["template_id"]
    cost["human_handoff"] = route["human_handoff"]

    return {"cost": cost}

