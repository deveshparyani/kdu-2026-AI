from pathlib import Path
import json
import os
import sys

import requests
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_BACKEND_URL = os.getenv("CHAT_BACKEND_URL", "http://127.0.0.1:8000")
REQUEST_TIMEOUT_SECONDS = 120


def initialize_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "usage_history" not in st.session_state:
        st.session_state.usage_history = []
    if "session_usage" not in st.session_state:
        st.session_state.session_usage = empty_usage()
    if "backend_url" not in st.session_state:
        st.session_state.backend_url = DEFAULT_BACKEND_URL
    if "pending_usage" not in st.session_state:
        st.session_state.pending_usage = None


def empty_usage() -> dict[str, int | float | None]:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "estimated_cost_usd": 0.0,
    }


def update_session_usage(usage: dict[str, int | float | None]) -> None:
    st.session_state.session_usage["input_tokens"] += usage["input_tokens"]
    st.session_state.session_usage["output_tokens"] += usage["output_tokens"]
    st.session_state.session_usage["total_tokens"] += usage["total_tokens"]

    current_cost = st.session_state.session_usage["estimated_cost_usd"]
    new_cost = usage.get("estimated_cost_usd")
    if current_cost is None or new_cost is None:
        st.session_state.session_usage["estimated_cost_usd"] = None
    else:
        st.session_state.session_usage["estimated_cost_usd"] = round(
            float(current_cost) + float(new_cost),
            6,
        )


def format_usage(usage: dict[str, int | float | None]) -> str:
    cost = usage.get("estimated_cost_usd")
    cost_text = "not configured" if cost is None else f"${cost:.6f}"
    return (
        f"Input: {usage['input_tokens']} | "
        f"Output: {usage['output_tokens']} | "
        f"Total: {usage['total_tokens']} | "
        f"Cost: {cost_text}"
    )


def stream_chat_api(messages: list[dict[str, str]], backend_url: str):
    response = requests.post(
        f"{backend_url.rstrip('/')}/chat/stream",
        json={"messages": messages},
        stream=True,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    if not response.ok:
        try:
            error_payload = response.json()
        except ValueError:
            error_payload = {"detail": response.text or "Unknown error"}

        detail = error_payload.get("detail", "Unable to process chat request.")
        raise RuntimeError(detail)

    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line:
            continue

        event = json.loads(raw_line)
        event_type = event.get("type")

        if event_type == "delta":
            yield event.get("delta", "")
        elif event_type == "usage":
            st.session_state.pending_usage = event.get("usage")
        elif event_type == "error":
            raise RuntimeError(event.get("detail", "Unable to process chat request."))


st.set_page_config(
    page_title="Multi-Function AI Assistant",
    page_icon="AI",
    layout="centered",
)

initialize_state()

st.title("Multi-Function AI Assistant")

with st.sidebar:
    st.subheader("Settings")
    st.session_state.backend_url = st.text_input(
        "Backend URL",
        value=st.session_state.backend_url,
        help="Example: http://127.0.0.1:8000",
    )

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.usage_history = []
        st.session_state.session_usage = empty_usage()
        st.session_state.pending_usage = None
        st.rerun()

    st.divider()
    st.subheader("Last Call Usage")
    last_usage = st.session_state.usage_history[-1] if st.session_state.usage_history else None
    if last_usage:
        st.metric("Input Tokens", last_usage["input_tokens"])
        st.metric("Output Tokens", last_usage["output_tokens"])
        st.metric("Total Tokens", last_usage["total_tokens"])
        cost = last_usage.get("estimated_cost_usd")
        if cost is None:
            st.write("Estimated Cost: not configured")
        else:
            st.write(f"Estimated Cost: ${cost:.6f}")
    else:
        st.write("No completed chat yet.")

    st.divider()
    st.subheader("Total Session Usage")
    total_usage = st.session_state.session_usage
    st.metric("Input Tokens", total_usage["input_tokens"])
    st.metric("Output Tokens", total_usage["output_tokens"])
    st.metric("Total Tokens", total_usage["total_tokens"])
    total_cost = total_usage.get("estimated_cost_usd")
    if total_cost is None:
        st.write("Estimated Cost: not configured")
    else:
        st.write(f"Estimated Cost: ${total_cost:.6f}")

    st.divider()
    st.subheader("Usage History")
    if st.session_state.usage_history:
        for index, usage in enumerate(reversed(st.session_state.usage_history), start=1):
            st.caption(f"Call {len(st.session_state.usage_history) - index + 1}: {format_usage(usage)}")
    else:
        st.write("No usage entries yet.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        usage = message.get("usage")
        if usage:
            st.caption(format_usage(usage))


prompt = st.chat_input("Ask something...")

if prompt:
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)
    st.session_state.pending_usage = None

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            response_placeholder = st.empty()
            response_placeholder.markdown("Thinking...")

            reply_chunks: list[str] = []
            for chunk in stream_chat_api(
                messages=st.session_state.messages,
                backend_url=st.session_state.backend_url,
            ):
                reply_chunks.append(chunk)
                response_placeholder.markdown("".join(reply_chunks))

            reply = "".join(reply_chunks)
            if not reply:
                reply = "I couldn't generate a response just now."
                response_placeholder.markdown(reply)

            usage = st.session_state.pending_usage
            if usage:
                st.caption(format_usage(usage))
                st.session_state.usage_history.append(usage)
                update_session_usage(usage)

            st.session_state.messages.append(
                {"role": "assistant", "content": reply, "usage": usage}
            )
        except requests.RequestException:
            error_message = (
                "Could not reach the backend. Make sure the FastAPI app is running."
            )
            st.error(error_message)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_message}
            )
        except RuntimeError as exc:
            error_message = str(exc)
            st.error(error_message)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_message}
            )
