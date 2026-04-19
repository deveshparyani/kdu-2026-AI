"""Command-line entry point for the FixIt workflow."""

from __future__ import annotations

import argparse
import json

from dotenv import load_dotenv

from app.graph import build_graph
from app.state import build_initial_state

DEFAULT_QUERY = "My plumber didn't show up, need refund"


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run the FixIt support workflow")
    parser.add_argument(
        "query",
        nargs="?",
        default=DEFAULT_QUERY,
        help="Customer support query to process",
    )
    parser.add_argument("--config-dir", default="config", help="Path to the config folder")
    parser.add_argument("--monthly-spend", type=float, default=0.0)
    parser.add_argument("--daily-query-count", type=int, default=0)
    args = parser.parse_args()

    graph = build_graph()
    initial_state = build_initial_state(
        query=args.query,
        config_dir=args.config_dir,
        monthly_spend_usd=args.monthly_spend,
        daily_query_count=args.daily_query_count,
    )
    result = graph.invoke(initial_state)

    output = {
        "classification": result["classification"],
        "route": result["route"],
        "response_text": result["response_text"],
        "cost": result["cost"],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
