"""Command-line interface for the tri-model assistant."""

import argparse

from src.graph import initialize_qa_session, run_assistant_workflow
from src.models import load_model_bundle
from src.qa import (
    answer_ambiguous_followup,
    answer_memory_question,
    build_qa_prompt,
    stream_answer_question,
)
from src.utils import print_section, read_multiline_text, read_text_from_file


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""

    parser = argparse.ArgumentParser(
        description="Run the local tri-model AI assistant."
    )
    parser.add_argument(
        "--input-file",
        type=str,
        help="Optional path to a text file used as the input document.",
    )
    parser.add_argument(
        "--summary-length",
        type=str,
        choices=["small", "medium", "large"],
        help="Optional summary size override for non-interactive runs.",
    )
    return parser


def get_input_text(input_file: str | None) -> str:
    """Resolve input text from either a file or terminal input."""

    return read_text_from_file(input_file) if input_file else read_multiline_text()


def map_summary_length(selection: str) -> str:
    """Map user-friendly length labels to internal prompt labels."""

    mapping = {
        "small": "short",
        "medium": "medium",
        "large": "long",
    }
    return mapping[selection]


def prompt_summary_length() -> str:
    """Ask the user which summary length they want."""

    print("\nChoose the refined summary length: small / medium / large")
    while True:
        choice = input("Summary length: ").strip().lower()
        if choice in {"small", "medium", "large"}:
            return map_summary_length(choice)

        print("Please enter one of: small, medium, or large.")


def run_cli() -> None:
    """Run the full interactive application."""

    parser = build_parser()
    args = parser.parse_args()
    input_text = get_input_text(args.input_file)
    summary_length = (
        map_summary_length(args.summary_length)
        if args.summary_length
        else prompt_summary_length()
    )

    if not input_text:
        raise ValueError("Please provide some input text before starting the app.")

    print("Loading local Hugging Face pipelines...")
    print("The first run may take a while because the models are downloaded locally.")
    model_bundle = load_model_bundle()

    print("\nRunning LangGraph workflow...")
    final_state = run_assistant_workflow(
        input_text=input_text,
        summary_length=summary_length,
        model_bundle=model_bundle,
    )

    print_section("Initial Summary", final_state["summary"] or "No summary generated.")
    print_section(
        "Refined Summary",
        final_state["refined_summary"] or "No refined summary generated.",
    )

    qa_app, qa_config = initialize_qa_session(
        base_state=final_state,
        model_bundle=model_bundle,
    )

    print('\nAsk questions about the refined summary. Type "exit" to quit.')
    while True:
        question = input("\nQuestion: ").strip()

        if question.lower() == "exit":
            print("Exiting the assistant.")
            break

        if not question:
            print("Please enter a question or type 'exit'.")
            continue

        current_state = qa_app.get_state(qa_config).values
        turn_state = {
            **current_state,
            "user_query": question,
            "is_exit": False,
        }

        direct_answer = answer_memory_question(turn_state, question)
        if direct_answer is None:
            direct_answer = answer_ambiguous_followup(question)

        if direct_answer is None:
            prompt = build_qa_prompt(
                state=turn_state,
                tokenizer=model_bundle.qa_tokenizer,
            )
            print("Answer: ", end="", flush=True)
            streamed_chunks: list[str] = []
            for chunk in stream_answer_question(model_bundle, prompt):
                print(chunk, end="", flush=True)
                streamed_chunks.append(chunk)
            print()
            answer = "".join(streamed_chunks).strip()
            if not answer:
                answer = "I could not find that information in the document or conversation."
        else:
            answer = direct_answer
            print(f"Answer: {answer}")

        qa_state = qa_app.invoke(
            {
                "user_query": question,
                "qa_response": None,
                "streamed_answer": answer,
                "is_exit": False,
            },
            config=qa_config,
        )
