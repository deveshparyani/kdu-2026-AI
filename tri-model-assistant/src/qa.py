"""QA helpers for prompt building, streaming, and simple memory handling."""

import re
from threading import Thread
from typing import Iterator

from transformers import TextIteratorStreamer

from src.models import ModelBundle
from src.state import AssistantState
from src.text_helpers import trim_text_to_token_budget
from src.utils import extract_generated_text


def answer_question(
    model_bundle: ModelBundle,
    prompt: str,
) -> str:
    """Answer a question with a generative QA prompt."""

    qa_inputs = model_bundle.qa_tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )
    qa_inputs = {
        key: value.to(model_bundle.qa_model.device)
        for key, value in qa_inputs.items()
    }
    output_tokens = model_bundle.qa_model.generate(
        **qa_inputs,
        max_new_tokens=120,
        do_sample=False,
        no_repeat_ngram_size=3,
        repetition_penalty=1.1,
    )
    answer = model_bundle.qa_tokenizer.decode(
        output_tokens[0],
        skip_special_tokens=True,
    ).strip()
    if answer.lower().startswith("if the answer is not available"):
        return "I could not find that information in the document or conversation."
    return answer or "I could not find that information in the document or conversation."


def stream_answer_question(
    model_bundle: ModelBundle,
    prompt: str,
) -> Iterator[str]:
    """Stream a generative QA answer token by token."""

    qa_inputs = model_bundle.qa_tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )
    qa_inputs = {
        key: value.to(model_bundle.qa_model.device)
        for key, value in qa_inputs.items()
    }
    streamer = TextIteratorStreamer(
        model_bundle.qa_tokenizer,
        skip_prompt=True,
        skip_special_tokens=True,
    )
    generation_kwargs = {
        **qa_inputs,
        "max_new_tokens": 120,
        "do_sample": False,
        "no_repeat_ngram_size": 3,
        "repetition_penalty": 1.1,
        "streamer": streamer,
    }
    worker = Thread(
        target=model_bundle.qa_model.generate,
        kwargs=generation_kwargs,
        daemon=True,
    )
    worker.start()
    try:
        for text in streamer:
            yield text
    finally:
        worker.join()


def build_qa_prompt(
    state: AssistantState,
    tokenizer: object | None = None,
    max_prompt_tokens: int = 420,
) -> str:
    """Build a generative QA prompt from document state."""

    input_text = state.get("input_text") or ""
    refined_summary = trim_text_to_token_budget(
        state.get("refined_summary") or "",
        max_tokens=120,
        tokenizer=tokenizer,
    )
    question = state.get("user_query") or ""
    detail_instruction = (
        "Give 3 to 5 concise factual points."
        if is_detail_question(question)
        else "Reply with one concise factual answer."
    )
    document_budget = 240 if is_detail_question(question) else 180

    trimmed_document = trim_text_to_token_budget(
        input_text,
        max_tokens=document_budget,
        tokenizer=tokenizer,
    )
    prompt = (
        "You are answering questions about a document.\n"
        "Use the document first and the refined summary as backup context.\n"
        "Do not give a generic restatement when the question asks for specific details.\n"
        f"{detail_instruction}\n"
        "If the answer is missing, reply exactly: I could not find that information.\n\n"
        f"Document:\n{trimmed_document}\n\n"
        f"Refined summary:\n{refined_summary}\n\n"
        f"Question:\n{question}\n\n"
        "Answer:"
    )
    return trim_text_to_token_budget(prompt, max_prompt_tokens, tokenizer=tokenizer)


def is_detail_question(question: str) -> bool:
    """Detect questions that ask for multiple concrete points."""

    normalized_question = question.strip().lower()
    detail_patterns = (
        "detail",
        "details",
        "what kind",
        "what are",
        "which are",
        "main areas",
        "components",
        "parts",
        "features",
        "pillars",
        "challenges",
        "recommend",
        "services",
    )
    return any(pattern in normalized_question for pattern in detail_patterns)


def answer_memory_question(state: AssistantState, question: str) -> str | None:
    """Handle simple memory questions directly from stored conversation state."""

    normalized_question = re.sub(r"[^a-z0-9\s]", "", question.strip().lower())
    history_turns = list(state.get("conversation_history", []))

    if (
        "last quest" in normalized_question
        or "previous quest" in normalized_question
        or "what did i ask" in normalized_question
    ):
        if not history_turns:
            return "You have not asked any previous question yet."

        last_turn = history_turns[-1]
        if last_turn.startswith("User: "):
            return last_turn.split("\nAssistant:", maxsplit=1)[0].replace("User: ", "", 1)

    if re.search(r"\b(last|previous)\s+answer\b", normalized_question):
        if not history_turns:
            return "I have not given any previous answer yet."

        last_turn = history_turns[-1]
        if "\nAssistant: " in last_turn:
            return last_turn.split("\nAssistant: ", maxsplit=1)[1]

    return None


def answer_ambiguous_followup(question: str) -> str | None:
    """Ask for clarification when the follow-up is too vague."""

    normalized_question = re.sub(r"[^a-z0-9\s]", "", question.strip().lower())
    if normalized_question in {"why", "how", "who", "what", "when", "where"}:
        return "Please ask a more specific question so I can answer it correctly."

    return None
