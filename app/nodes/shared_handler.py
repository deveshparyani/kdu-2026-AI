"""Shared category handler logic."""

from __future__ import annotations

from app.services.llm_client import LLMClient
from app.services.model_registry import get_model_config
from app.services.prompt_manager import load_prompt_file, render_prompt
from app.services.router import select_route
from app.state import FixItState


def run_category_handler(state: FixItState, category: str) -> dict:
    """Load the route, prompt, and model, then generate a response."""

    if state["classification"]["category"] != category:
        raise ValueError(
            f"Expected category '{category}', got '{state['classification']['category']}'"
        )

    route = select_route(
        config=state["config"],
        classification=state["classification"],
        budget_status=state["budget_status"],
    )

    prompt_data = load_prompt_file(
        config=state["config"],
        config_dir=state.get("config_dir", "config"),
        prompt_reference=route["prompt"],
    )

    rendered_prompt = render_prompt(
        prompt_data,
        {
            "query": state["query"],
            "category": category,
            "complexity": route["complexity"],
            "response_type": route["response_type"],
        },
    )

    client = LLMClient()
    model_config = get_model_config(state["config"], route["model"])
    llm_result = client.generate_response(
        query=state["query"],
        rendered_prompt=rendered_prompt,
        model_name=route["model"],
        category=category,
        human_handoff=route["human_handoff"],
        model_config=model_config,
    )

    return {
        "route": route,
        "prompt": prompt_data,
        "llm_result": llm_result,
        "response_text": llm_result["text"],
    }
