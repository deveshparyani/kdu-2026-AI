"""Why this file exists: it provides beginner-friendly in-memory storage."""

from threading import Lock

from .models import (
    ActionRecord,
    ActionResponse,
    ChatMessage,
    DemoUser,
    HiddenActionEvent,
    SessionRecord,
    ThreadRecord,
)
from .security import generate_message_id, generate_thread_id, utc_now_iso


class InMemoryStore:
    """
    Very small in-memory store for the learning phases.

    Security choice:
    We keep users, thread ownership, sessions, and message history in server
    memory so the flow stays easy to understand. The same ownership rules still
    apply even though this is not a real database yet.
    """

    def __init__(self) -> None:
        self.lock = Lock()
        self.users: dict[str, DemoUser] = {}
        self.thread_ownership: dict[str, ThreadRecord] = {}
        self.sessions: dict[str, SessionRecord] = {}
        self.thread_messages: dict[str, list[ChatMessage]] = {}
        self.thread_hidden_actions: dict[str, list[HiddenActionEvent]] = {}
        self.action_records: dict[str, ActionRecord] = {}


STORE = InMemoryStore()


def reset_store() -> None:
    """Clear the store so tests can start from a clean state."""

    with STORE.lock:
        STORE.users.clear()
        STORE.thread_ownership.clear()
        STORE.sessions.clear()
        STORE.thread_messages.clear()
        STORE.thread_hidden_actions.clear()
        STORE.action_records.clear()


def get_or_create_user(user_id: str) -> DemoUser:
    """Return an existing user or create one the first time we see the header."""

    with STORE.lock:
        existing = STORE.users.get(user_id)
        if existing:
            return existing

        user = DemoUser(user_id=user_id, created_at=utc_now_iso())
        STORE.users[user_id] = user
        return user


def create_thread_for_user(user_id: str) -> ThreadRecord:
    """Create a new thread owned by one authenticated user."""

    with STORE.lock:
        thread = ThreadRecord(
            thread_id=generate_thread_id(),
            user_id=user_id,
            created_at=utc_now_iso(),
            mode="ai",
        )
        STORE.thread_ownership[thread.thread_id] = thread
        STORE.thread_messages[thread.thread_id] = []
        STORE.thread_hidden_actions[thread.thread_id] = []
        return thread


def get_thread(thread_id: str) -> ThreadRecord | None:
    """Look up one thread by id."""

    return STORE.thread_ownership.get(thread_id)


def update_thread_mode(*, thread_id: str, mode: str) -> ThreadRecord:
    """
    Update one thread's mode in memory.

    Security choice:
    The mode lives on the server-owned thread record so the browser cannot
    decide on its own whether AI is paused or resumed.
    """

    with STORE.lock:
        thread = STORE.thread_ownership[thread_id]
        updated_thread = thread.model_copy(update={"mode": mode})
        STORE.thread_ownership[thread_id] = updated_thread
        return updated_thread


def list_threads_for_user(user_id: str) -> list[ThreadRecord]:
    """
    Return only the threads owned by one user.

    Security choice:
    Listing is filtered on the server. The frontend never decides which
    thread records it is allowed to see.
    """

    return [
        thread
        for thread in STORE.thread_ownership.values()
        if thread.user_id == user_id
    ]


def list_thread_messages(thread_id: str) -> list[ChatMessage]:
    """Return visible chat history for one thread."""

    return STORE.thread_messages.get(thread_id, []).copy()


def append_thread_message(
    *,
    thread_id: str,
    role: str,
    content: str,
    widgets: list | None = None,
) -> ChatMessage:
    """Append one visible chat message to a thread."""

    with STORE.lock:
        message = ChatMessage(
            id=generate_message_id("msg"),
            role=role,
            content=content,
            created_at=utc_now_iso(),
            widgets=widgets or [],
        )
        STORE.thread_messages.setdefault(thread_id, []).append(message)
        return message


def append_hidden_action_event(
    *,
    thread_id: str,
    action_type: str,
    widget_id: str,
    payload,
) -> HiddenActionEvent:
    """
    Append one hidden action event to a thread.

    Security choice:
    Hidden widget actions are stored separately from visible messages so they do
    not pretend to be normal user chat content.
    """

    with STORE.lock:
        event = HiddenActionEvent(
            id=generate_message_id("event"),
            action_type=action_type,
            widget_id=widget_id,
            payload=payload,
            created_at=utc_now_iso(),
        )
        STORE.thread_hidden_actions.setdefault(thread_id, []).append(event)
        return event


def save_session(
    *,
    client_secret: str,
    thread_id: str,
    user_id: str,
    model: str,
    provider: str,
) -> SessionRecord:
    """Store a session record keyed by the returned client secret."""

    with STORE.lock:
        session = SessionRecord(
            client_secret=client_secret,
            thread_id=thread_id,
            user_id=user_id,
            model=model,
            created_at=utc_now_iso(),
            provider=provider,
        )
        STORE.sessions[client_secret] = session
        return session


def build_action_scope_key(
    *,
    user_id: str,
    thread_id: str,
    widget_id: str,
    action_type: str,
    idempotency_key: str,
) -> str:
    """Create one in-memory key for idempotent action tracking."""

    return ":".join([user_id, thread_id, widget_id, action_type, idempotency_key])


def get_action_response_by_scope_key(scope_key: str) -> ActionResponse | None:
    """Return a previous action result if this idempotency key was already used."""

    record = STORE.action_records.get(scope_key)
    if record is None:
        return None

    return ActionResponse(
        status="success",
        message=record.message,
        assistant_message=record.assistant_message,
    )


def save_action_response(
    *,
    scope_key: str,
    user_id: str,
    thread_id: str,
    widget_id: str,
    action_type: str,
    idempotency_key: str,
    message: str,
    assistant_message: ChatMessage,
) -> ActionResponse:
    """
    Store the first successful action result.

    Security choice:
    Saving the result against an idempotency key lets the server safely ignore
    repeat clicks without performing the same action twice.
    """

    with STORE.lock:
        record = ActionRecord(
            idempotency_key=idempotency_key,
            thread_id=thread_id,
            widget_id=widget_id,
            user_id=user_id,
            action_type=action_type,
            message=message,
            assistant_message=assistant_message,
            created_at=utc_now_iso(),
        )
        STORE.action_records[scope_key] = record
        return ActionResponse(
            status="success",
            message=message,
            assistant_message=assistant_message,
        )
