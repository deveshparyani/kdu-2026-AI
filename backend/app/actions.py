"""Why this file exists: it handles button clicks or widget actions from the frontend."""

from .db import get_offer_by_id
from .models import ActionRequest, ActionResponse


def handle_action(request: ActionRequest) -> ActionResponse:
    """Return a friendly placeholder response for a selected travel offer."""

    offer = get_offer_by_id(request.offer_id)
    if not offer:
        return ActionResponse(message="Sorry, that offer could not be found.")

    return ActionResponse(
        message=(
            f"You selected '{offer.title}'. "
            "TODO: connect this action to a real booking or handoff flow."
        )
    )
