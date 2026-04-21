"""Utility helpers used across the project."""

import re
from pathlib import Path
from typing import Any


def chunk_text(text: str, max_words: int = 350) -> list[str]:
    """Split large text into simple word-based chunks."""

    words = text.split()
    if not words:
        return []

    return [
        " ".join(words[index : index + max_words])
        for index in range(0, len(words), max_words)
    ]


def extract_generated_text(result: object) -> str:
    """Normalize common Hugging Face pipeline outputs into a plain string."""

    if isinstance(result, list) and result:
        first_item = result[0]
        if isinstance(first_item, dict):
            return str(
                first_item.get("summary_text")
                or first_item.get("generated_text")
                or first_item.get("answer")
                or ""
            ).strip()

    if isinstance(result, dict):
        return str(
            result.get("summary_text")
            or result.get("generated_text")
            or result.get("answer")
            or ""
        ).strip()

    return str(result).strip()


def count_text_tokens(text: str, tokenizer: Any | None = None) -> int:
    """Estimate token count with a tokenizer when available."""

    if not text.strip():
        return 0

    if tokenizer is not None:
        if hasattr(tokenizer, "backend_tokenizer"):
            return len(tokenizer.backend_tokenizer.encode(text).ids)
        if hasattr(tokenizer, "tokenize"):
            return len(tokenizer.tokenize(text))
        if hasattr(tokenizer, "encode"):
            return len(tokenizer.encode(text, add_special_tokens=False))

    return len(text.split())


def format_history_turn(question: str, answer: str) -> str:
    """Format one QA turn for short-term memory."""

    return f"User: {question}\nAssistant: {answer}"


def join_history_turns(turns: list[str]) -> str:
    """Join history turns into a readable block."""

    return "\n\n".join(turns).strip()


def build_refinement_prompt(
    summary: str,
    summary_length: str,
) -> str:
    """Create a refinement prompt that respects the requested summary length."""

    length_guidance = {
        "short": "Keep the final summary very brief, around 2 to 3 sentences.",
        "medium": "Keep the final summary balanced, around 4 to 6 sentences.",
        "long": "Keep the final summary detailed, around 7 to 10 sentences.",
    }
    selected_guidance = length_guidance.get(
        summary_length,
        length_guidance["medium"],
    )

    return (
        "Refine the draft summary so it is clear, factual, and well structured.\n"
        f"Requested length: {summary_length}.\n"
        f"{selected_guidance}\n"
        "Write complete sentences and do not copy the prompt.\n\n"
        f"Draft summary:\n{summary}\n\n"
        "Refined summary:"
    )


def clean_generated_summary(text: str) -> str:
    """Remove repeated sentences and unfinished trailing fragments."""

    cleaned_text = text.strip()
    if not cleaned_text:
        return cleaned_text

    sentence_matches = re.findall(r"[^.!?]+[.!?]?", cleaned_text)
    seen: set[str] = set()
    unique_sentences: list[str] = []

    for sentence in sentence_matches:
        normalized = " ".join(sentence.lower().split()).strip(" .!?")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_sentences.append(sentence.strip())

    result = " ".join(sentence for sentence in unique_sentences if sentence)
    if result and result[-1] not in ".!?":
        words = result.split()
        if len(words) < 8:
            return ""
        result = result + "."

    return result.strip()


def read_text_from_file(path: str) -> str:
    """Read input text from a file path."""

    return Path(path).read_text(encoding="utf-8").strip()


def read_multiline_text() -> str:
    """Read large text input from the terminal until the user types END."""

    print("Paste your source text below. Type END on a new line when finished.")
    lines: list[str] = []

    while True:
        try:
            line = input()
        except EOFError:
            break

        if line.strip() == "END":
            break

        lines.append(line)

    return "\n".join(lines).strip()


def print_section(title: str, content: str) -> None:
    """Display a section in the terminal."""

    print(f"\n{title}")
    print("-" * len(title))
    print(content)
