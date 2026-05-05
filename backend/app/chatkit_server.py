"""Why this file exists: it isolates ChatKit and assistant-model helpers."""

from openai import OpenAI

from .config import Settings, get_settings
from .models import ChatMessage
from .security import generate_demo_client_secret
from .tools import looks_like_travel_request
from .widgets import TravelOfferWidget


def create_chatkit_client_secret(user_id: str, thread_id: str) -> tuple[str, str]:
    """
    Create a client secret for one authenticated user and one thread.

    Security choice:
    This wrapper is the only place that knows about OpenAI credentials.
    The frontend gets only the returned client secret, never `OPENAI_API_KEY`.

    Returns:
        tuple[str, str]: (client_secret, provider_name)
    """

    settings = get_settings()

    if settings.openai_api_key and settings.chatkit_workflow_id:
        client = OpenAI(api_key=settings.openai_api_key)

        try:
            # TODO:
            # Replace this block with the exact ChatKit SDK call your project
            # decides to use. The current docs show the server creating a
            # session and passing a unique `user` value from the backend.
            #
            # We keep the uncertain SDK details here so the rest of the app can
            # stay focused on session security and thread ownership.
            session = client.chatkit.sessions.create(  # type: ignore[attr-defined]
                {
                    "workflow": {"id": settings.chatkit_workflow_id},
                    "user": user_id,
                    "thread": {"id": thread_id},
                }
            )
            return session.client_secret, "openai"  # type: ignore[no-any-return]
        except Exception:
            # Demo-friendly fallback:
            # if the SDK call shape changes or the local environment is not
            # ready yet, we still return a fake secret so students can keep
            # testing thread ownership and message flows.
            pass

    return generate_demo_client_secret(), "demo"


def generate_travel_assistant_text(
    *,
    user_message: str,
    recent_messages: list[ChatMessage],
    widgets: list[TravelOfferWidget],
    settings: Settings,
) -> str:
    """
    Generate one small assistant reply.

    We keep the prompt short and cheap because this assignment is meant to be
    easy to read and inexpensive to try.
    """

    if settings.openai_api_key:
        client = OpenAI(api_key=settings.openai_api_key)
        conversation_preview = "\n".join(
            f"{message.role}: {message.content}" for message in recent_messages[-4:]
        )
        widget_hint = (
            "A travel offer widget will be shown after your reply."
            if widgets
            else "No widget will be shown."
        )

        try:
            response = client.responses.create(
                model=settings.openai_model,
                input=(
                    "You are a concise travel booking assistant. "
                    "Reply in under 90 words. Be friendly and practical.\n\n"
                    f"Recent conversation:\n{conversation_preview}\n\n"
                    f"Latest user request: {user_message}\n"
                    f"{widget_hint}"
                ),
                max_output_tokens=140,
            )
            if response.output_text.strip():
                return response.output_text.strip()
        except Exception:
            # If the API call fails, we fall back to a deterministic local reply
            # so the app still works for learning and demo purposes.
            pass

    if widgets:
        featured_offer = widgets[0]
        return (
            f"I found an option that matches your request. "
            f"{featured_offer.title} is currently {featured_offer.price}, and "
            f"it includes {featured_offer.description.lower()}. "
            "You can review the offer card below and click Book Now if you want "
            "to continue."
        )

    if looks_like_travel_request(user_message):
        return (
            "I can help with that travel plan. Share your destination, dates, "
            "and budget, and I will suggest a simple option."
        )

    return (
        "I can help with trips, flights, hotels, weekends, and budgets. "
        "Tell me where you want to go and how much you want to spend."
    )
