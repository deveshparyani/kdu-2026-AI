"""Tests for shared state helpers."""

import pytest

from src.state import create_default_state


def test_create_default_state_strips_input() -> None:
    state = create_default_state("  Example input text.  ")

    assert state["input_text"] == "Example input text."
    assert state["summary_length"] == "medium"
    assert state["summary"] is None
    assert state["refined_summary"] is None
    assert state["user_query"] is None
    assert state["qa_response"] is None
    assert state["streamed_answer"] is None
    assert state["conversation_history"] == []
    assert state["history_summary"] is None
    assert state["is_exit"] is False


def test_create_default_state_rejects_empty_text() -> None:
    with pytest.raises(ValueError):
        create_default_state("   ")
