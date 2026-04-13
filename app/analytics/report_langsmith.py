import json
import os
from typing import Any

from dotenv import load_dotenv
from langsmith import Client

load_dotenv()


def build_project_report(project_name: str, limit: int = 20) -> dict[str, Any]:
    """Summarize recent root traces for a LangSmith project."""
    client = Client()
    runs = list(
        client.list_runs(
            project_name=project_name,
            is_root=True,
            limit=limit,
        )
    )

    traces = []
    totals = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
    }

    for run in runs:
        prompt_tokens = run.prompt_tokens or 0
        completion_tokens = run.completion_tokens or 0
        total_tokens = run.total_tokens or 0
        total_cost = float(run.total_cost or 0.0)

        traces.append(
            {
                "id": str(run.id),
                "name": run.name,
                "run_type": run.run_type,
                "start_time": run.start_time.isoformat() if run.start_time else None,
                "total_tokens": total_tokens,
                "total_cost_usd": total_cost,
                "error": run.error,
            }
        )

        totals["prompt_tokens"] += prompt_tokens
        totals["completion_tokens"] += completion_tokens
        totals["total_tokens"] += total_tokens
        totals["total_cost_usd"] = round(totals["total_cost_usd"] + total_cost, 8)

    return {
        "project_name": project_name,
        "trace_count": len(traces),
        "totals": totals,
        "traces": traces,
    }


if __name__ == "__main__":
    project_name = os.getenv("LANGSMITH_PROJECT", "stock-trading-agent")
    report = build_project_report(project_name)
    print(json.dumps(report, indent=2))
