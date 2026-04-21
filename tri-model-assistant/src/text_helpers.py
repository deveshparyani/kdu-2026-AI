"""Text processing helpers for summarization and refinement."""

import re

from src.utils import count_text_tokens

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "were",
    "with",
}


def should_keep_original_summary(
    original_summary: str,
    refined_summary: str,
    summary_length: str,
) -> bool:
    """Keep the original summary when refinement drops too much key content."""

    original_keywords = {
        word
        for word in re.findall(r"[a-zA-Z]+", original_summary.lower())
        if len(word) > 3 and word not in STOPWORDS
    }
    refined_keywords = {
        word
        for word in re.findall(r"[a-zA-Z]+", refined_summary.lower())
        if len(word) > 3 and word not in STOPWORDS
    }

    if not original_keywords:
        return False

    overlap_ratio = len(original_keywords & refined_keywords) / len(original_keywords)
    if overlap_ratio < 0.25:
        return True

    if summary_length in {"medium", "long"}:
        original_word_count = len(original_summary.split())
        refined_word_count = len(refined_summary.split())
        if refined_word_count < max(12, int(original_word_count * 0.75)):
            return True

    return False


def trim_text_to_token_budget(
    text: str,
    max_tokens: int,
    tokenizer: object | None = None,
) -> str:
    """Trim text so it stays within a simple token budget."""

    if count_text_tokens(text, tokenizer) <= max_tokens:
        return text

    words = text.split()
    while words and count_text_tokens(" ".join(words), tokenizer) > max_tokens:
        words = words[:-25]

    return " ".join(words).strip()
