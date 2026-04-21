"""LangGraph node builders for the assistant workflow."""

from src.models import ModelBundle
from src.qa import (
    answer_ambiguous_followup,
    answer_memory_question,
    answer_question,
    build_qa_prompt,
)
from src.state import AssistantState
from src.text_helpers import should_keep_original_summary, trim_text_to_token_budget
from src.utils import (
    build_refinement_prompt,
    clean_generated_summary,
    chunk_text,
    count_text_tokens,
    extract_generated_text,
    format_history_turn,
    join_history_turns,
)


def make_summarize_node(model_bundle: ModelBundle):
    """Create the summarization node."""

    def summarize_node(state: AssistantState) -> AssistantState:
        text = state["input_text"]
        chunks = chunk_text(text)
        summary_length = state.get("summary_length", "medium")
        summary_config = {
            "short": {"max_length": 90, "min_length": 30},
            "medium": {"max_length": 130, "min_length": 40},
            "long": {"max_length": 200, "min_length": 70},
        }
        selected_config = summary_config.get(summary_length, summary_config["medium"])

        if not chunks:
            raise ValueError("The summarization node received empty input.")

        partial_summaries: list[str] = []
        for chunk in chunks:
            summarizer_tokenizer = getattr(model_bundle.summarizer, "tokenizer", None)
            input_tokens = count_text_tokens(chunk, summarizer_tokenizer)
            target_max_length = min(
                selected_config["max_length"],
                max(selected_config["min_length"] + 10, int(input_tokens * 0.65)),
            )
            target_min_length = min(
                selected_config["min_length"],
                max(20, target_max_length - 20),
            )
            result = model_bundle.summarizer(
                chunk,
                max_length=target_max_length,
                min_length=target_min_length,
                do_sample=False,
            )
            partial_summaries.append(extract_generated_text(result))

        merged_summary = " ".join(partial_summaries).strip()
        return {"summary": merged_summary}

    return summarize_node


def make_refine_node(model_bundle: ModelBundle):
    """Create the refinement node."""

    def refine_node(state: AssistantState) -> AssistantState:
        summary = state["summary"] or ""
        summary_length = state.get("summary_length", "medium")
        refiner_tokenizer = getattr(model_bundle.refiner, "tokenizer", None)
        trimmed_summary = trim_text_to_token_budget(
            summary,
            max_tokens=160,
            tokenizer=refiner_tokenizer,
        )
        prompt = build_refinement_prompt(
            trimmed_summary,
            summary_length,
        )
        max_new_tokens_by_length = {
            "short": 90,
            "medium": 180,
            "long": 280,
        }
        result = model_bundle.refiner(
            prompt,
            max_new_tokens=max_new_tokens_by_length.get(summary_length, 180),
            do_sample=False,
            no_repeat_ngram_size=3,
            repetition_penalty=1.15,
        )
        refined_summary = clean_generated_summary(extract_generated_text(result)) or summary
        if should_keep_original_summary(
            original_summary=summary,
            refined_summary=refined_summary,
            summary_length=summary_length,
        ):
            refined_summary = summary

        return {
            "refined_summary": refined_summary,
        }

    return refine_node


def make_qa_node(
    model_bundle: ModelBundle,
    max_prompt_tokens: int = 420,
):
    """Create the QA node used in the interactive loop."""

    def qa_node(state: AssistantState) -> AssistantState:
        question = (state.get("user_query") or "").strip()
        if not question or state.get("is_exit", False):
            return {}

        memory_answer = answer_memory_question(state, question)
        if memory_answer is not None:
            updated_history = list(state.get("conversation_history", []))
            updated_history.append(format_history_turn(question, memory_answer))
            return {
                "qa_response": memory_answer,
                "conversation_history": updated_history,
            }

        clarification = answer_ambiguous_followup(question)
        if clarification is not None:
            updated_history = list(state.get("conversation_history", []))
            updated_history.append(format_history_turn(question, clarification))
            return {
                "qa_response": clarification,
                "conversation_history": updated_history,
            }

        precomputed_answer = state.get("streamed_answer")
        if precomputed_answer:
            updated_history = list(state.get("conversation_history", []))
            updated_history.append(format_history_turn(question, precomputed_answer))
            return {
                "qa_response": precomputed_answer,
                "streamed_answer": None,
                "conversation_history": updated_history,
            }

        qa_tokenizer = model_bundle.qa_tokenizer
        prompt = build_qa_prompt(
            state=state,
            tokenizer=qa_tokenizer,
            max_prompt_tokens=max_prompt_tokens,
        )
        answer = answer_question(
            model_bundle=model_bundle,
            prompt=prompt,
        )

        updated_history = list(state.get("conversation_history", []))
        updated_history.append(format_history_turn(question, answer))

        return {
            "qa_response": answer,
            "streamed_answer": None,
            "conversation_history": updated_history,
        }

    return qa_node


def make_history_summary_node(
    model_bundle: ModelBundle,
    history_token_limit: int = 220,
    keep_recent_turns: int = 2,
):
    """Create the post-QA summarization middleware node."""

    def summarize_history_node(state: AssistantState) -> AssistantState:
        history_turns = list(state.get("conversation_history", []))
        if len(history_turns) <= keep_recent_turns:
            return {}

        history_summary = state.get("history_summary") or ""
        history_text = join_history_turns(history_turns)
        refiner_tokenizer = getattr(model_bundle.refiner, "tokenizer", None)
        total_tokens = count_text_tokens(
            "\n\n".join(part for part in [history_summary, history_text] if part.strip()),
            tokenizer=refiner_tokenizer,
        )

        if total_tokens <= history_token_limit:
            return {}

        older_turns = history_turns[:-keep_recent_turns]
        recent_turns = history_turns[-keep_recent_turns:]
        summary_source_parts = []

        if history_summary:
            summary_source_parts.append(f"Previous conversation summary:\n{history_summary}")

        summary_source_parts.append(f"Older conversation turns:\n{join_history_turns(older_turns)}")

        prompt = (
            "Summarize the following conversation history so that future question "
            "answering can keep the important context. Keep names, facts, and "
            "open references.\n\n"
            f"{chr(10).join(summary_source_parts)}\n\n"
            "Updated conversation summary:"
        )
        result = model_bundle.refiner(
            prompt,
            max_new_tokens=180,
            do_sample=False,
        )
        updated_summary = extract_generated_text(result) or history_summary

        return {
            "history_summary": updated_summary,
            "conversation_history": recent_turns,
        }

    return summarize_history_node
