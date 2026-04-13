import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from langsmith import Client, evaluate
from langsmith.schemas import Example, Run

from app.analytics.runner import run_agent_turn

load_dotenv()

EVAL_EXAMPLES_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "evaluation_examples.json"
)


def load_evaluation_examples() -> list[dict[str, Any]]:
    """Load local evaluation examples."""
    with EVAL_EXAMPLES_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def summarize_agent_output(result: dict[str, Any]) -> dict[str, Any]:
    """Convert the graph state into a compact shape for evaluation."""
    if "__interrupt__" in result:
        interrupt_value = result["__interrupt__"][0].value
        return {
            "response_type": "approval_interrupt",
            "stock": interrupt_value.get("stock"),
            "currency": interrupt_value.get("currency"),
            "message_present": bool(interrupt_value.get("message")),
        }

    if result.get("portfolio_details"):
        return {
            "response_type": "portfolio",
            "stock": None,
            "currency": result["portfolio_details"].get("currency"),
            "message_present": bool(result["portfolio_details"].get("message")),
        }

    if result.get("transaction_history"):
        return {
            "response_type": "transactions",
            "stock": None,
            "currency": None,
            "message_present": bool(result["transaction_history"].get("message")),
        }

    if result.get("stock_price_response"):
        return {
            "response_type": "stock_price",
            "stock": result["stock_price_response"].get("stock"),
            "currency": result["stock_price_response"].get("currency"),
            "message_present": bool(result["stock_price_response"].get("message")),
        }

    if result.get("assistant_response"):
        return {
            "response_type": "unknown_reply",
            "stock": None,
            "currency": None,
            "message_present": bool(result.get("assistant_response")),
        }

    return {
        "response_type": "unknown_output",
        "stock": None,
        "currency": None,
        "message_present": False,
    }


def evaluation_target(inputs: dict[str, Any]) -> dict[str, Any]:
    """Run the agent on one evaluation example."""
    user_query = inputs["user_query"]
    base_state = dict(inputs.get("state", {}))

    result = run_agent_turn(
        state=base_state,
        user_query=user_query,
        thread_id=f"eval-{uuid4()}",
    )
    return summarize_agent_output(result)


def response_type_match(run: Run, example: Example) -> dict[str, Any]:
    """Check whether the agent chose the expected response path."""
    predicted = run.outputs["response_type"]
    expected = example.outputs["response_type"]
    return {
        "key": "response_type_match",
        "score": predicted == expected,
    }


def currency_match(run: Run, example: Example) -> dict[str, Any]:
    """Check whether the returned currency matches when expected."""
    expected_currency = (example.outputs or {}).get("currency")
    if not expected_currency:
        return {"key": "currency_match", "score": True}

    return {
        "key": "currency_match",
        "score": run.outputs.get("currency") == expected_currency,
    }


def stock_match(run: Run, example: Example) -> dict[str, Any]:
    """Check whether the stock symbol matches when expected."""
    expected_stock = (example.outputs or {}).get("stock")
    if not expected_stock:
        return {"key": "stock_match", "score": True}

    return {
        "key": "stock_match",
        "score": run.outputs.get("stock") == expected_stock,
    }


def message_present(run: Run, example: Example) -> dict[str, Any]:
    """Check that the agent returned a non-empty user-facing message."""
    return {
        "key": "message_present",
        "score": bool(run.outputs.get("message_present")),
    }


def run_evaluation(upload_results: bool | None = None):
    """Run a basic LangSmith evaluation over local examples."""
    examples = load_evaluation_examples()
    client = Client()

    if client.api_key:
        dataset_name = f"stock-trading-agent-eval-{uuid4()}"
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="Basic evaluation dataset for the stock trading agent.",
        )
        client.create_examples(
            dataset_id=dataset.id,
            examples=examples,
        )

        if upload_results is None:
            upload_results = True

        return evaluate(
            evaluation_target,
            data=dataset_name,
            evaluators=[
                response_type_match,
                currency_match,
                stock_match,
                message_present,
            ],
            experiment_prefix="stock-trading-agent-basic-eval",
            description="Basic routing and output evaluation for the stock trading agent.",
            metadata={"agent_version": "v1"},
            client=client,
            upload_results=upload_results,
        )

    return run_local_evaluation(examples)


def run_local_evaluation(
    examples: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run a small local evaluation when LangSmith credentials are unavailable."""
    evaluation_examples = examples or load_evaluation_examples()
    rows = []
    metric_totals = {
        "response_type_match": 0,
        "currency_match": 0,
        "stock_match": 0,
        "message_present": 0,
    }

    for example in evaluation_examples:
        predicted = evaluation_target(example["inputs"])
        expected = example["outputs"]

        row_metrics = {
            "response_type_match": predicted["response_type"] == expected["response_type"],
            "currency_match": (
                True
                if not expected.get("currency")
                else predicted.get("currency") == expected["currency"]
            ),
            "stock_match": (
                True
                if not expected.get("stock")
                else predicted.get("stock") == expected["stock"]
            ),
            "message_present": bool(predicted.get("message_present")),
        }

        for key, value in row_metrics.items():
            metric_totals[key] += int(value)

        rows.append(
            {
                "query": example["inputs"]["user_query"],
                "predicted": predicted,
                "expected": expected,
                "metrics": row_metrics,
            }
        )

    example_count = len(evaluation_examples)
    averages = {
        key: round(value / example_count, 4)
        for key, value in metric_totals.items()
    }

    return {
        "mode": "local",
        "example_count": example_count,
        "summary": averages,
        "rows": rows,
    }


if __name__ == "__main__":
    results = run_evaluation()
    print(results)
