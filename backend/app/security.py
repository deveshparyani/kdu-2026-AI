"""Why this file exists: it keeps small security helpers in one place."""

from datetime import UTC, datetime
import re
import secrets


USER_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,40}$")
THREAD_ID_PATTERN = re.compile(r"^thread_[a-zA-Z0-9_-]{8,80}$")


def is_valid_demo_user_id(value: str) -> bool:
    """
    Allow only a short, simple demo user id.

    Security choice:
    Keeping the allowed format small makes the demo easier to reason about
    and avoids odd values in logs, dictionaries, and tests.
    """

    return bool(USER_ID_PATTERN.fullmatch(value))


def is_valid_thread_id(value: str) -> bool:
    """Check that a thread id matches the format our backend generates."""

    return bool(THREAD_ID_PATTERN.fullmatch(value))


def utc_now_iso() -> str:
    """Return a simple UTC timestamp string for in-memory records."""

    return datetime.now(UTC).isoformat()


def generate_thread_id() -> str:
    """
    Generate a backend-owned thread id.

    Security choice:
    We generate thread ids on the server instead of trusting the frontend.
    Random ids make guessing other users' ids harder.
    """

    return f"thread_{secrets.token_urlsafe(12)}"


def generate_demo_client_secret() -> str:
    """
    Generate a fake client secret for the learning demo.

    Security choice:
    The frontend only receives a scoped client secret, never the API key.
    """

    return f"cs_demo_{secrets.token_urlsafe(24)}"


def generate_message_id(prefix: str = "msg") -> str:
    """Generate a short random id for chat messages and hidden events."""

    return f"{prefix}_{secrets.token_urlsafe(8)}"
