from uuid import uuid4

from dotenv import load_dotenv

from app.analytics.runner import resume_agent_turn, run_agent_turn

load_dotenv()


def print_agent_response(result: dict):
    """Print the most useful response from the graph state."""
    if "__interrupt__" in result:
        interrupt_value = result["__interrupt__"][0].value
        print(f"\nApproval needed: {interrupt_value['message']}")
        return

    if result.get("portfolio_details"):
        print(f"\n{result['portfolio_details']['message']}")
        return

    if result.get("stock_price_response"):
        print(f"\n{result['stock_price_response']['message']}")
        return

    if result.get("transaction_history"):
        print(f"\n{result['transaction_history']['message']}")
        return

    if result.get("trade_result"):
        print(f"\n{result['trade_result']['message']}")
        return

    if result.get("assistant_response"):
        print(f"\n{result['assistant_response']}")
        return

    print("\nNo response was produced.")


def print_observability_summary(result: dict):
    """Print a short token and cost summary for the current state."""
    observability = result.get("observability", {})
    totals = observability.get("totals")
    if not totals:
        return

    print(
        "\nObservability:"
        f" input_tokens={totals['input_tokens']},"
        f" output_tokens={totals['output_tokens']},"
        f" total_tokens={totals['total_tokens']},"
        f" estimated_cost_usd={totals['estimated_cost_usd']}"
    )


def main():
    thread_id = str(uuid4())
    state = {
        "portfolio": {},
        "transactions": [],
        "currency": "USD",
    }

    print("Stock Trading Agent")
    print("Type 'exit' to quit.\n")

    while True:
        user_query = input("You: ").strip()
        if user_query.lower() in {"exit", "quit"}:
            break

        result = run_agent_turn(
            state=state,
            user_query=user_query,
            thread_id=thread_id,
        )

        print_agent_response(result)
        print_observability_summary(result)
        state = result

        while "__interrupt__" in result:
            answer = input("\nApprove trade? (yes/no): ").strip()
            result = resume_agent_turn(
                thread_id=thread_id,
                answer=answer,
            )
            print_agent_response(result)
            print_observability_summary(result)
            state = result


if __name__ == "__main__":
    main()
