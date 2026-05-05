"""Why this file exists: it handles demo authentication from request headers."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from .config import Settings, get_settings
from .db import get_or_create_user
from .models import DemoUser
from .security import is_valid_demo_user_id


async def get_authenticated_user(
    settings: Annotated[Settings, Depends(get_settings)],
    x_demo_user_id: Annotated[str | None, Header(alias="X-Demo-User-Id")] = None,
) -> DemoUser:
    """
    Authenticate the request using `X-Demo-User-Id`.

    Security choice:
    We read the user identity only from the request header. We do not accept
    `user_id` in request bodies because the client must not choose who it is.
    """

    if x_demo_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Missing X-Demo-User-Id header. "
                "Send a demo user id such as user_a or user_b."
            ),
        )

    candidate = x_demo_user_id.strip()
    if not is_valid_demo_user_id(candidate):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid X-Demo-User-Id header. "
                "Use 3-40 letters, numbers, hyphens, or underscores."
            ),
        )

    # Demo-only behavior:
    # the first time we see a user id, we create a record in memory.
    _ = settings
    return get_or_create_user(candidate)
