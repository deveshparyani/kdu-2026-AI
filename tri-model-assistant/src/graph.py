"""Graph construction for the tri-model workflow."""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.models import ModelBundle, load_model_bundle
from src.nodes import (
    make_history_summary_node,
    make_qa_node,
    make_refine_node,
    make_summarize_node,
)
from src.state import AssistantState, create_default_state


def build_assistant_graph(model_bundle: ModelBundle):
    """Build and compile the LangGraph workflow."""

    workflow = StateGraph(AssistantState)
    workflow.add_node("summarize", make_summarize_node(model_bundle))
    workflow.add_node("refine", make_refine_node(model_bundle))
    workflow.add_edge(START, "summarize")
    workflow.add_edge("summarize", "refine")
    workflow.add_edge("refine", END)
    return workflow.compile()


def build_qa_graph(
    model_bundle: ModelBundle,
    history_token_limit: int = 220,
):
    """Build and compile the checkpointed QA graph."""

    workflow = StateGraph(AssistantState)
    workflow.add_node("qa", make_qa_node(model_bundle))
    workflow.add_node(
        "summarize_history",
        make_history_summary_node(
            model_bundle=model_bundle,
            history_token_limit=history_token_limit,
        ),
    )
    workflow.add_edge(START, "qa")
    workflow.add_edge("qa", "summarize_history")
    workflow.add_edge("summarize_history", END)
    return workflow.compile(checkpointer=MemorySaver())


def run_assistant_workflow(
    input_text: str,
    summary_length: str = "medium",
    model_bundle: ModelBundle | None = None,
) -> AssistantState:
    """Run the summarization and refinement stages."""

    bundle = model_bundle or load_model_bundle()
    app = build_assistant_graph(bundle)
    return app.invoke(create_default_state(input_text, summary_length=summary_length))


def initialize_qa_session(
    base_state: AssistantState,
    model_bundle: ModelBundle,
    thread_id: str = "qa-session",
    history_token_limit: int = 220,
):
    """Seed a checkpointed QA graph with the summary state."""

    qa_app = build_qa_graph(
        model_bundle=model_bundle,
        history_token_limit=history_token_limit,
    )
    config = {"configurable": {"thread_id": thread_id}}
    qa_app.invoke(base_state, config=config)
    return qa_app, config
