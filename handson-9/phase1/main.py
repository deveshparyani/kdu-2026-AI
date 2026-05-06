from __future__ import annotations

import json
import os
import re
import time
import warnings
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from langsmith import traceable, tracing_context
from langsmith.wrappers import wrap_openai
from nemoguardrails import LLMRails, RailsConfig
from openai import OpenAI

from backend import get_user_data

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
ENV_FILE = BASE_DIR / ".env"
ROOT_ENV_FILE = BASE_DIR.parent / ".env"

MODEL_NAME = "gpt-4.1-nano"
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
TRACE_TRIGGER_PATTERNS = [
    r"\bssn\b",
    r"\bsocial\s+security\b",
    r"\bignore\s+(all\s+)?previous\s+instructions\b",
    r"\bjailbreak\b",
    r"\breveal\s+internal\s+(information|data)\b",
    r"\bprint\s+(all\s+)?stored\s+(profile\s+data|user\s+information)\b",
    r"\bshow\s+confidential\s+data\b",
    r"\boutput\s+the\s+complete\s+customer\s+profile\b",
]
SSN_DEMO_REQUEST_PATTERNS = [
    r"\bssn\b",
    r"\bsocial\s+security\b",
]
SYSTEM_PROMPT = (
    "You are a customer support assistant helping users with account-related "
    "questions. You have access to customer profile information and should use "
    "it when relevant to assist the user accurately."
)
SSN_DEMO_SYSTEM_PROMPT = (
    f"{SYSTEM_PROMPT} This is an educational observability drill using "
    "fictional mock customer data. For SSN account questions in this demo, "
    "include the full mock SSN exactly once so the output guardrail can show "
    "redaction in the next span."
)


@dataclass
class ChatbotResult:
    """Response plus observability metadata for one chatbot turn."""

    assistant_reply: str
    raw_reply: str | None
    raw_latency_ms: float | None
    guarded_latency_ms: float
    input_blocked: bool
    output_modified: bool
    raw_contains_ssn: bool
    final_contains_ssn: bool
    ssn_demo_fallback_used: bool

    @property
    def guardrail_triggered(self) -> bool:
        """Return True when a guardrail blocked or modified the request."""
        return self.input_blocked or self.output_modified

    def trace_metadata(self) -> dict[str, bool | float | None]:
        """Return LangSmith-friendly metadata for filtering traces."""
        return {
            "input_blocked": self.input_blocked,
            "output_modified": self.output_modified,
            "raw_contains_ssn": self.raw_contains_ssn,
            "final_contains_ssn": self.final_contains_ssn,
            "ssn_demo_fallback_used": self.ssn_demo_fallback_used,
            "raw_latency_ms": self.raw_latency_ms,
            "guarded_latency_ms": self.guarded_latency_ms,
            "guardrail_triggered": self.guardrail_triggered,
        }


warnings.filterwarnings(
    "ignore",
    message=r"The class `ChatOpenAI` was deprecated.*",
    category=Warning,
)
warnings.filterwarnings(
    "ignore",
    message=r"You are trying to use a chat model.*",
    category=Warning,
)


def build_insecure_prompt(user_message: str) -> str:
    """Build a prompt that intentionally includes sensitive backend data.

    This keeps the educational demo realistic: sensitive data is still present
    in the LLM context, and the guardrails reduce what can safely come back out.
    """
    sensitive_user_data = get_user_data()
    serialized_user_data = json.dumps(sensitive_user_data, indent=2)

    demo_instruction = ""
    if is_ssn_demo_request(user_message):
        demo_instruction = (
            "\n\nEducational observability drill:\n"
            "For this mock-data demo only, answer SSN account questions by "
            "including the customer's full mock SSN exactly once. This is "
            "intentional so the output guardrail can demonstrate masking."
        )

    return (
        "Internal customer profile data:\n"
        f"{serialized_user_data}\n\n"
        "Customer message:\n"
        f"{user_message}"
        f"{demo_instruction}"
    )


@traceable(name="deterministic_ssn_demo_raw_output", run_type="chain")
def build_ssn_demo_raw_reply() -> str:
    """Create deterministic vulnerable raw output for the SSN masking demo."""
    return f"Your SSN is {get_user_data()['ssn']}."


def create_client() -> OpenAI:
    """Create the OpenAI client after loading variables from .env."""
    load_dotenv(ENV_FILE)

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key == "your_api_key_here":
        # Helpful when running from the repo root during workshops.
        load_dotenv(ROOT_ENV_FILE, override=True)
        api_key = os.getenv("OPENAI_API_KEY")

    if not api_key or api_key == "your_api_key_here":
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Add it to the .env file before running "
            "the chatbot."
        )

    return wrap_openai(OpenAI(api_key=api_key), completions_name="openai.responses.create")


def create_guardrails() -> LLMRails:
    """Load the local NeMo Guardrails configuration."""
    config = RailsConfig.from_path(str(CONFIG_DIR))
    return LLMRails(config)


def get_response_text(response: object) -> str:
    """Extract text from NeMo's common response shapes.

    Without logging, LLMRails usually returns a dictionary. With generation
    options, it may return a GenerationResponse object. This helper keeps the
    beginner-facing code in the chat loop simple.
    """
    if isinstance(response, dict):
        return str(response.get("content", ""))

    response_items = getattr(response, "response", None)
    if response_items and isinstance(response_items, list):
        return str(response_items[0].get("content", ""))

    return str(response)


@traceable(name="input_guardrail_check", run_type="chain")
def run_input_rails(rails: LLMRails, user_message: str) -> str:
    """Run only NeMo input rails against the user's message."""
    response = rails.generate(
        messages=[{"role": "user", "content": user_message}],
        options={"rails": ["input"]},
    )
    return get_response_text(response)


@traceable(name="raw_openai_generation", run_type="chain")
def generate_unfiltered_reply(client: OpenAI, user_message: str) -> tuple[str, float, bool]:
    """Call the OpenAI Responses API before output guardrails are applied."""
    started_at = time.perf_counter()
    response = client.responses.create(
        model=MODEL_NAME,
        instructions=SSN_DEMO_SYSTEM_PROMPT
        if is_ssn_demo_request(user_message)
        else SYSTEM_PROMPT,
        input=build_insecure_prompt(user_message),
    )
    latency_ms = (time.perf_counter() - started_at) * 1000

    raw_reply = response.output_text or "[The model returned no text output.]"
    fallback_used = False
    if is_ssn_demo_request(user_message) and not contains_ssn(raw_reply):
        raw_reply = build_ssn_demo_raw_reply()
        fallback_used = True

    return raw_reply, latency_ms, fallback_used


def run_output_rails(
    rails: LLMRails, user_message: str, assistant_message: str
) -> str:
    """Run only NeMo output rails against the generated assistant message."""
    response = rails.generate(
        messages=[
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message},
        ],
        options={"rails": ["output"]},
    )
    return get_response_text(response)


@traceable(name="output_guardrail_check", run_type="chain")
def traced_run_output_rails(
    rails: LLMRails, user_message: str, assistant_message: str
) -> str:
    """Trace the output rail as the point where masking/refusal can happen."""
    return run_output_rails(rails, user_message, assistant_message)


def contains_ssn(text: str | None) -> bool:
    """Return True when text contains an unmasked SSN pattern."""
    return bool(text and SSN_PATTERN.search(text))


def is_ssn_demo_request(user_message: str) -> bool:
    """Return True for prompts intended to exercise SSN output masking."""
    return any(
        re.search(pattern, user_message, flags=re.IGNORECASE)
        for pattern in SSN_DEMO_REQUEST_PATTERNS
    )


def looks_like_guardrail_demo_prompt(user_message: str) -> bool:
    """Precheck likely guardrail/PII scenarios for trace sampling."""
    return any(
        re.search(pattern, user_message, flags=re.IGNORECASE)
        for pattern in TRACE_TRIGGER_PATTERNS
    )


def should_trace_turn(user_message: str) -> bool:
    """Decide whether to enable LangSmith tracing for this turn."""
    tracing_enabled = os.getenv("LANGSMITH_TRACING", "").lower() == "true"
    if not tracing_enabled:
        return False

    api_key = os.getenv("LANGSMITH_API_KEY", "")
    if not api_key or api_key == "your_langsmith_api_key_here":
        return False

    sample_mode = os.getenv("LANGSMITH_SAMPLE_MODE", "guardrail_events").lower()
    if sample_mode == "all":
        return True

    if sample_mode == "guardrail_events":
        return looks_like_guardrail_demo_prompt(user_message)

    # These modes are described in the README as production strategies. They
    # need always-on or buffered tracing to capture the full nested call tree.
    if sample_mode in {"high_latency", "failed"}:
        return False

    return False


def tracing_status_message(user_message: str, trace_enabled: bool) -> str:
    """Explain why LangSmith tracing is on or off for the current turn."""
    if trace_enabled:
        return "on"

    if os.getenv("LANGSMITH_TRACING", "").lower() != "true":
        return "off; LANGSMITH_TRACING is not true"

    api_key = os.getenv("LANGSMITH_API_KEY", "")
    if not api_key or api_key == "your_langsmith_api_key_here":
        return "off; LANGSMITH_API_KEY is missing or still a placeholder"

    sample_mode = os.getenv("LANGSMITH_SAMPLE_MODE", "guardrail_events").lower()
    if sample_mode == "guardrail_events":
        return "off; prompt did not match guardrail/PII sampling rules"

    if sample_mode in {"high_latency", "failed"}:
        return f"off; {sample_mode} is documented but not captured in this CLI demo"

    return f"off; unknown LANGSMITH_SAMPLE_MODE={sample_mode}"


def trace_context_metadata(user_message: str) -> dict[str, bool | str]:
    """Create metadata available on captured LangSmith traces."""
    return {
        "sample_mode": os.getenv("LANGSMITH_SAMPLE_MODE", "guardrail_events"),
        "likely_guardrail_demo": looks_like_guardrail_demo_prompt(user_message),
    }


def trace_context_tags(user_message: str) -> list[str]:
    """Create searchable tags for the LangSmith trace."""
    tags = ["phase1", "nemo-guardrails"]
    if looks_like_guardrail_demo_prompt(user_message):
        tags.append("likely_guardrail_event")
    return tags


@traceable(name="phase1_guarded_chatbot_turn", run_type="chain")
def get_guarded_reply(
    client: OpenAI, rails: LLMRails, user_message: str
) -> ChatbotResult:
    """Generate a response through input rails, the LLM, and output rails."""
    guarded_started_at = time.perf_counter()

    checked_input = run_input_rails(rails, user_message)
    if checked_input != user_message:
        guarded_latency_ms = (time.perf_counter() - guarded_started_at) * 1000
        return ChatbotResult(
            assistant_reply=checked_input,
            raw_reply=None,
            raw_latency_ms=None,
            guarded_latency_ms=guarded_latency_ms,
            input_blocked=True,
            output_modified=False,
            raw_contains_ssn=False,
            final_contains_ssn=contains_ssn(checked_input),
            ssn_demo_fallback_used=False,
        )

    unfiltered_reply, raw_latency_ms, ssn_demo_fallback_used = generate_unfiltered_reply(
        client, user_message
    )
    final_reply = traced_run_output_rails(rails, user_message, unfiltered_reply)

    guarded_latency_ms = (time.perf_counter() - guarded_started_at) * 1000
    return ChatbotResult(
        assistant_reply=final_reply,
        raw_reply=unfiltered_reply,
        raw_latency_ms=raw_latency_ms,
        guarded_latency_ms=guarded_latency_ms,
        input_blocked=False,
        output_modified=final_reply != unfiltered_reply,
        raw_contains_ssn=contains_ssn(unfiltered_reply),
        final_contains_ssn=contains_ssn(final_reply),
        ssn_demo_fallback_used=ssn_demo_fallback_used,
    )


def main() -> None:
    """Run a small terminal chatbot loop."""
    client = create_client()
    rails = create_guardrails()

    print("Guarded customer support chatbot")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_message:
            print("Assistant: Please enter a message.\n")
            continue

        if user_message.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        try:
            trace_enabled = should_trace_turn(user_message)
            with tracing_context(
                enabled=trace_enabled,
                project_name=os.getenv(
                    "LANGSMITH_PROJECT", "phase1-guardrails-observability"
                ),
                tags=trace_context_tags(user_message),
                metadata=trace_context_metadata(user_message),
            ):
                result = get_guarded_reply(
                    client,
                    rails,
                    user_message,
                    langsmith_extra={
                        "metadata": {
                            "model": MODEL_NAME,
                            "sampling_decision": trace_enabled,
                        }
                    },
                )
        except Exception as error:
            print(f"Assistant: Request failed: {error}\n")
            continue

        print(f"Assistant: {result.assistant_reply}")
        if result.raw_latency_ms is None:
            print("Raw LLM latency before guardrails: skipped; input rail blocked it")
        else:
            print(f"Raw LLM latency before output rails: {result.raw_latency_ms:.0f} ms")
        print(
            "Guarded pipeline latency after guardrails: "
            f"{result.guarded_latency_ms:.0f} ms"
        )
        print(
            "LangSmith tracing for this turn: "
            f"{tracing_status_message(user_message, trace_enabled)}"
        )
        print(f"Guardrail metadata: {result.trace_metadata()}\n")


if __name__ == "__main__":
    main()
