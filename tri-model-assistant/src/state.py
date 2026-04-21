"""Shared state definitions for the LangGraph workflow."""

from typing import Optional, TypedDict


class AssistantState(TypedDict):
    """State shared across the LangGraph workflow and QA loop."""

    # The full source text provided by the user.
    input_text: str
    # A simple user preference that controls summary size, such as short or medium.
    summary_length: str
    # The first summary produced by the summarization model.
    summary: Optional[str]
    # The improved version of the summary produced by the refinement model.
    refined_summary: Optional[str]
    # The most recent question asked by the user in the QA loop.
    user_query: Optional[str]
    # The most recent answer returned by the QA model.
    qa_response: Optional[str]
    # A precomputed streamed answer that should be saved into memory.
    streamed_answer: Optional[str]
    # A short rolling list of recent question-answer pairs.
    conversation_history: list[str]
    # A compact summary of older QA turns after history compression.
    history_summary: Optional[str]
    # True when the user wants to stop the interactive loop.
    is_exit: bool


def create_default_state(
    input_text: str,
    summary_length: str = "medium",
) -> AssistantState:
    """Return a clean default state for a new assistant run."""

    cleaned_text = input_text.strip()
    if not cleaned_text:
        raise ValueError("Input text cannot be empty.")

    return {
        "input_text": cleaned_text,
        "summary_length": summary_length,
        "summary": None,
        "refined_summary": None,
        "user_query": None,
        "qa_response": None,
        "streamed_answer": None,
        "conversation_history": [],
        "history_summary": None,
        "is_exit": False,
    }
