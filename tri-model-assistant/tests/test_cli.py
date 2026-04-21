"""Tests for CLI helpers."""

from src.cli import map_summary_length, prompt_summary_length


def test_map_summary_length_converts_user_labels() -> None:
    assert map_summary_length("small") == "short"
    assert map_summary_length("medium") == "medium"
    assert map_summary_length("large") == "long"


def test_prompt_summary_length_retries_until_valid(monkeypatch, capsys) -> None:
    answers = iter(["tiny", "large"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    result = prompt_summary_length()

    assert result == "long"
    captured = capsys.readouterr()
    assert "Please enter one of: small, medium, or large." in captured.out
