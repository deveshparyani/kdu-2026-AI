import numexpr as ne


def calculator(expression: str) -> str:
    try:
        return str(ne.evaluate(expression))
    except Exception as exc:  # pragma: no cover - numexpr raises varied exceptions
        return f"Unable to evaluate expression: {exc}"
