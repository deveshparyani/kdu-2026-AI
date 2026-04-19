"""Classify the support query."""

from __future__ import annotations

from app.services.llm_client import LLMClient
from app.services.model_registry import get_model_config
from app.state import FixItState


def orchestrator_classifier_node(state: FixItState) -> dict:
    client = LLMClient()
    model_name = state["config"]["orchestrator"]["model"]
    model_config = get_model_config(state["config"], model_name)
    result = client.classify_query(
        state["query"],
        model_name=model_name,
        model_config=model_config,
    )
    return {"classification": result["classification"]}
