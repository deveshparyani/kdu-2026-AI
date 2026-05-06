"""AWS Bedrock Guardrails + local Llama 3 8B chatbot demo."""

from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv

from aws_guardrail import BedrockGuardrail, GuardrailResult
from backend import get_user_data
from local_llm import OllamaClient

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

DEFAULT_REFUSAL = "I cannot safely respond to that request."


def load_settings() -> dict[str, str]:
    """Load required settings from phase2/.env or the shell environment."""
    load_dotenv(ENV_FILE)

    settings = {
        "aws_region": os.getenv("AWS_REGION", "us-east-1"),
        "aws_profile": os.getenv("AWS_PROFILE", ""),
        "guardrail_id": os.getenv("BEDROCK_GUARDRAIL_ID", ""),
        "guardrail_version": os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT"),
        "output_scope": os.getenv("BEDROCK_OUTPUT_SCOPE", "FULL"),
        "ollama_model": os.getenv("OLLAMA_MODEL", "llama3:8b"),
        "ollama_url": os.getenv("OLLAMA_URL", "http://localhost:11434"),
    }

    if not settings["guardrail_id"] or settings["guardrail_id"] == "your_guardrail_id_here":
        raise RuntimeError(
            "BEDROCK_GUARDRAIL_ID is missing. Create a phase2/.env file from "
            ".env.example and set your AWS Bedrock Guardrail ID."
        )

    return settings


def choose_guarded_text(original_text: str, result: GuardrailResult) -> str:
    """Use Bedrock's blocked/masked text when it intervenes."""
    if result.intervened:
        return result.text or DEFAULT_REFUSAL

    return original_text


def print_guardrail_summary(label: str, result: GuardrailResult) -> None:
    """Print a compact summary of the AWS guardrail assessment."""
    status = "blocked/masked" if result.intervened else "allowed"
    print(f"{label} guardrail: {result.action} ({status}, {result.latency_ms:.0f} ms)")

    if not result.findings:
        print("  Findings: none reported")
        return

    print("  Findings:")
    for finding in result.findings:
        print(
            "  - "
            f"{finding.policy} | {finding.type} | "
            f"confidence={finding.confidence} | "
            f"filterStrength={finding.filter_strength} | "
            f"action={finding.action}"
        )


def handle_prompt(
    *,
    user_prompt: str,
    guardrail: BedrockGuardrail,
    llm: OllamaClient,
) -> None:
    """Run one prompt through input guardrail, local LLM, and output guardrail."""
    total_started_at = time.perf_counter()

    input_result = guardrail.apply(user_prompt, "INPUT")
    if input_result.intervened:
        final_text = choose_guarded_text(user_prompt, input_result)
        total_latency_ms = (time.perf_counter() - total_started_at) * 1000

        print(f"\nAssistant: {final_text}\n")
        print_guardrail_summary("Input", input_result)
        print("Local LLM: skipped because input guardrail intervened")
        print(f"Total latency: {total_latency_ms:.0f} ms\n")
        return

    customer_profile = get_user_data()
    print("Mock backend: customer profile added to local LLM context")
    llm_result = llm.generate(user_prompt, customer_profile)
    output_result = guardrail.apply(llm_result.text, "OUTPUT")
    final_text = choose_guarded_text(llm_result.text, output_result)
    total_latency_ms = (time.perf_counter() - total_started_at) * 1000

    print(f"\nAssistant: {final_text}\n")
    print_guardrail_summary("Input", input_result)
    print(f"Local LLM: {llm_result.latency_ms:.0f} ms")
    print_guardrail_summary("Output", output_result)
    print(f"Total latency: {total_latency_ms:.0f} ms\n")


def main() -> None:
    """Run the terminal chatbot."""
    settings = load_settings()

    guardrail = BedrockGuardrail(
        region_name=settings["aws_region"],
        guardrail_id=settings["guardrail_id"],
        guardrail_version=settings["guardrail_version"],
        output_scope=settings["output_scope"],
        profile_name=settings["aws_profile"] or None,
    )
    aws_identity = guardrail.validate_credentials()
    llm = OllamaClient(
        base_url=settings["ollama_url"],
        model=settings["ollama_model"],
    )
    llm.validate_ready()

    print("AWS Bedrock Guardrails + local Llama 3 8B demo")
    print(f"AWS identity: {aws_identity}")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_prompt = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_prompt:
            print("Assistant: Please enter a prompt.\n")
            continue

        if user_prompt.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        try:
            handle_prompt(user_prompt=user_prompt, guardrail=guardrail, llm=llm)
        except Exception as error:
            print(f"\nError: {error}\n")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"Configuration error: {error}")
