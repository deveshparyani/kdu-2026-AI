import os

def calculate_usage(response) -> dict[str, int | float | None]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": None,
        }

    input_tokens = getattr(usage, "input_tokens", 0)
    output_tokens = getattr(usage, "output_tokens", 0)
    total_tokens = getattr(usage, "total_tokens", input_tokens + output_tokens)

    input_cost_per_million = os.getenv("OPENAI_INPUT_COST_PER_MILLION")
    output_cost_per_million = os.getenv("OPENAI_OUTPUT_COST_PER_MILLION")
    estimated_cost_usd = None

    if input_cost_per_million and output_cost_per_million:
        input_cost = (input_tokens / 1_000_000) * float(input_cost_per_million)
        output_cost = (output_tokens / 1_000_000) * float(output_cost_per_million)
        estimated_cost_usd = round(input_cost + output_cost, 6)

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": estimated_cost_usd,
    }
