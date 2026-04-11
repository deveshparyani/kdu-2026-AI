from dataclasses import dataclass
from typing import Literal

from app.core.config import get_settings


@dataclass
class RoutingDecision:
    input_type: Literal["text", "multimodal"]
    style: Literal["default", "expert", "child"]
    model_name: str


# This function checks whether the current request contains an image.
def detect_input_type(image_url: str | None) -> Literal["text", "multimodal"]:
    if image_url:
        return "multimodal"
    return "text"


# This function looks for style hints inside the current user message.
def detect_style_from_message(message: str) -> Literal["expert", "child"] | None:
    text = message.lower()

    child_keywords = [
        "like a child",
        "for a child",
        "for kids",
        "for a kid",
        "simple words",
        "very simple",
        "explain simply",
        "eli5",
    ]
    expert_keywords = [
        "expert mode",
        "technical",
        "advanced",
        "deep dive",
        "be concise and technical",
        "for an expert",
    ]

    for keyword in child_keywords:
        if keyword in text:
            return "child"

    for keyword in expert_keywords:
        if keyword in text:
            return "expert"

    return None


# This function looks for style hints in recent short-term memory.
def detect_style_from_thread(
    thread_messages: list[dict[str, str]],
) -> Literal["expert", "child"] | None:
    for message in reversed(thread_messages):
        if message["role"] != "user":
            continue

        style = detect_style_from_message(message["content"])
        if style:
            return style

    return None


# This function picks the final communication style using the agreed priority order.
def select_style(
    user_message: str,
    thread_messages: list[dict[str, str]],
    request_style: str,
    long_term_style: str | None,
) -> Literal["default", "expert", "child"]:
    message_style = detect_style_from_message(user_message)
    if message_style:
        return message_style

    thread_style = detect_style_from_thread(thread_messages)
    if thread_style:
        return thread_style

    if request_style in {"expert", "child"}:
        return request_style

    if long_term_style in {"expert", "child"}:
        return long_term_style

    return "default"


# This function chooses the right model based on the detected input type.
def select_model_name(input_type: Literal["text", "multimodal"]) -> str:
    settings = get_settings()

    if input_type == "multimodal":
        return settings.vision_model

    return settings.text_model


# This function combines input detection, style selection, and model selection.
def build_routing_decision(
    user_message: str,
    image_url: str | None,
    thread_messages: list[dict[str, str]],
    request_style: str,
    long_term_style: str | None,
) -> RoutingDecision:
    input_type = detect_input_type(image_url)
    style = select_style(user_message, thread_messages, request_style, long_term_style)
    model_name = select_model_name(input_type)

    return RoutingDecision(
        input_type=input_type,
        style=style,
        model_name=model_name,
    )
