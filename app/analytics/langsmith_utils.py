import json
from pathlib import Path
from typing import Any

from langsmith import get_current_run_tree


PRICING_FILE = Path(__file__).resolve().parent.parent / "data" / "groq_model_pricing.json"


def load_model_pricing() -> dict[str, Any]:
    """Load simple model pricing data used for cost observations."""
    with PRICING_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def extract_usage_metadata(response: Any) -> dict[str, Any]:
    """Pull token usage from a LangChain model response."""
    usage = getattr(response, "usage_metadata", None) or {}
    input_tokens = int(usage.get("input_tokens", 0))
    output_tokens = int(usage.get("output_tokens", 0))
    total_tokens = int(usage.get("total_tokens", input_tokens + output_tokens))

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def calculate_llm_cost(model_name: str, usage_metadata: dict[str, Any]) -> dict[str, float]:
    """Estimate LLM input/output cost from token counts and pricing data."""
    pricing = load_model_pricing().get("models", {}).get(model_name, {})
    input_price = pricing.get("input_cost_per_1m_tokens", 0.0)
    output_price = pricing.get("output_cost_per_1m_tokens", 0.0)

    input_tokens = usage_metadata.get("input_tokens", 0)
    output_tokens = usage_metadata.get("output_tokens", 0)

    input_cost = round((input_tokens / 1_000_000) * input_price, 8)
    output_cost = round((output_tokens / 1_000_000) * output_price, 8)
    total_cost = round(input_cost + output_cost, 8)

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
    }


def _build_observability_update(
    existing_observability: dict[str, Any],
    *,
    step_name: str,
    model_name: str,
    usage_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Append one LLM observation and update aggregate totals."""
    previous = existing_observability or {}
    llm_calls = list(previous.get("llm_calls", []))
    totals = dict(
        previous.get(
            "totals",
            {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
            },
        )
    )

    call_observation = {
        "step": step_name,
        "model": model_name,
        "input_tokens": usage_metadata["input_tokens"],
        "output_tokens": usage_metadata["output_tokens"],
        "total_tokens": usage_metadata["total_tokens"],
        "estimated_cost_usd": usage_metadata["total_cost"],
    }
    llm_calls.append(call_observation)

    totals["input_tokens"] += usage_metadata["input_tokens"]
    totals["output_tokens"] += usage_metadata["output_tokens"]
    totals["total_tokens"] += usage_metadata["total_tokens"]
    totals["estimated_cost_usd"] = round(
        totals["estimated_cost_usd"] + usage_metadata["total_cost"],
        8,
    )

    return {
        "llm_calls": llm_calls,
        "totals": totals,
    }


def record_llm_observation(
    state: dict[str, Any],
    *,
    step_name: str,
    model_name: str,
    response: Any,
    provider: str = "groq",
) -> dict[str, Any]:
    """
    Record token usage and estimated cost both in LangSmith and in local state.
    """
    usage_metadata = extract_usage_metadata(response)
    cost_metadata = calculate_llm_cost(model_name, usage_metadata)
    combined_usage = {
        **usage_metadata,
        **cost_metadata,
    }

    current_run = get_current_run_tree()
    if current_run is not None:
        current_run.add_metadata(
            {
                "ls_provider": provider,
                "ls_model_name": model_name,
                "observed_step": step_name,
            }
        )
        current_run.set(usage_metadata=combined_usage)

    return _build_observability_update(
        state.get("observability", {}),
        step_name=step_name,
        model_name=model_name,
        usage_metadata=combined_usage,
    )
