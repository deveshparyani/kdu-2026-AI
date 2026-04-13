from typing import Any
from uuid import uuid4

from langsmith import traceable
from langgraph.types import Command

from app.graph.workflow import stock_trading_graph


def build_graph_config(thread_id: str) -> dict[str, Any]:
    """Build the graph config used for checkpointing and tracing threads."""
    return {
        "configurable": {
            "thread_id": thread_id,
        },
        "metadata": {
            "thread_id": thread_id,
            "session_id": thread_id,
        },
    }


@traceable(run_type="chain", name="agent_turn")
def run_agent_turn(
    *,
    state: dict[str, Any],
    user_query: str,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """Run one user turn through the compiled graph."""
    active_thread_id = thread_id or str(uuid4())
    graph_input = dict(state)
    graph_input["user_query"] = user_query

    return stock_trading_graph.invoke(
        graph_input,
        config=build_graph_config(active_thread_id),
    )


@traceable(run_type="chain", name="agent_resume")
def resume_agent_turn(
    *,
    thread_id: str,
    answer: str,
) -> dict[str, Any]:
    """Resume an interrupted graph turn with a yes/no human response."""
    return stock_trading_graph.invoke(
        Command(resume=answer),
        config=build_graph_config(thread_id),
    )
