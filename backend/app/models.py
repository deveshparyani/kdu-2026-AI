"""Why this file exists: it defines the small backend data shapes used by the app."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .widgets import TravelOfferActionPayload, TravelOfferWidget


ThreadMode = Literal["ai", "human"]


class DemoUser(BaseModel):
    """A demo user record stored in memory."""

    user_id: str
    created_at: str


class ChatMessage(BaseModel):
    """
    One visible chat message in a thread.

    We keep widgets on the assistant message that introduced them so the
    frontend can render widgets inline inside the conversation.
    """

    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: str
    widgets: list[TravelOfferWidget] = Field(default_factory=list)


class HiddenActionEvent(BaseModel):
    """
    One hidden widget action stored in the thread timeline.

    Security choice:
    This is not shown as a user message. It is an internal event that records
    what happened when a widget button was clicked.
    """

    id: str
    action_type: Literal["book_now"]
    widget_id: str
    payload: TravelOfferActionPayload
    created_at: str


class ThreadRecord(BaseModel):
    """A thread and the user who owns it."""

    thread_id: str
    user_id: str
    created_at: str
    mode: ThreadMode


class SessionRecord(BaseModel):
    """A stored ChatKit session record for demo purposes."""

    client_secret: str
    thread_id: str
    user_id: str
    model: str
    created_at: str
    provider: Literal["demo", "openai"]


class SessionRequest(BaseModel):
    """
    Input for creating or continuing a chat session.

    Security choice:
    We forbid extra fields so the browser cannot sneak in a `user_id`
    or unrelated values and hope the backend will trust them.
    """

    model_config = ConfigDict(extra="forbid")

    thread_id: str | None = Field(
        default=None,
        description="Existing thread id to continue. If missing, create a new thread.",
    )


class SessionResponse(BaseModel):
    """Response returned to the frontend after session creation."""

    client_secret: str
    thread_id: str
    user_id: str
    mode: ThreadMode
    messages: list[ChatMessage] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """
    One visible chat message request from the user.

    Security choice:
    The body contains the thread id and visible text only. User identity still
    comes from the `X-Demo-User-Id` header.
    """

    model_config = ConfigDict(extra="forbid")

    thread_id: str
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    """One assistant response that the frontend can render in the chat window."""

    thread_id: str
    mode: ThreadMode
    assistant_message: ChatMessage


class ChatResponseEvent(BaseModel):
    """
    One streaming event for real-time assistant text.

    This is intentionally simple. It mimics the kind of incremental events a
    ChatKit or provider streaming API would produce.
    """

    type: Literal["assistant_delta", "done"]
    text: str | None = None


class WidgetEvent(BaseModel):
    """A streaming event that inserts a widget into the assistant response."""

    type: Literal["widget"] = "widget"
    widget: TravelOfferWidget


class ThreadListItem(BaseModel):
    """Small thread summary returned by GET /api/threads."""

    thread_id: str
    user_id: str
    created_at: str
    mode: ThreadMode


class ThreadListResponse(BaseModel):
    """Only the authenticated user's threads should appear here."""

    threads: list[ThreadListItem]


class DebugCreateThreadResponse(BaseModel):
    """Response for the demo-only thread creation route."""

    thread_id: str
    user_id: str
    mode: ThreadMode


class ActionRequest(BaseModel):
    """
    Hidden widget action sent by the frontend.

    Security choice:
    This is not a visible chat message. It is a hidden event emitted by a UI
    widget, so the backend must validate every field before using it.
    """

    model_config = ConfigDict(extra="forbid")

    thread_id: str
    widget_id: str
    action_type: Literal["book_now"]
    payload: TravelOfferActionPayload
    idempotency_key: str = Field(min_length=8, max_length=200)


class ActionResponse(BaseModel):
    """Response after the backend accepts a hidden widget action."""

    status: Literal["success"]
    message: str
    assistant_message: ChatMessage


class ActionRecord(BaseModel):
    """Stored result for one idempotent widget action."""

    idempotency_key: str
    thread_id: str
    widget_id: str
    user_id: str
    action_type: str
    message: str
    assistant_message: ChatMessage
    created_at: str


class ThreadModeResponse(BaseModel):
    """Current thread mode for the handoff panel."""

    mode: ThreadMode


class ThreadHandoffResponse(BaseModel):
    """Response after starting or ending human handoff."""

    mode: ThreadMode
    message: str
