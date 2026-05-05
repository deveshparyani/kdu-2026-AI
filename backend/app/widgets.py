"""Why this file exists: it defines the server-driven widget schema for Phase 2."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


TRAVEL_OFFER_WIDGET_TYPE = "travel_offer"
BOOK_NOW_ACTION_TYPE = "book_now"


class TravelOfferActionPayload(BaseModel):
    """Small action payload sent back when a user clicks a widget button."""

    offer_id: str


class TravelOfferAction(BaseModel):
    """One action the frontend can render as a button."""

    type: Literal["book_now"]
    label: str
    payload: TravelOfferActionPayload


class TravelOfferWidget(BaseModel):
    """
    Server-defined UI shape for one travel offer card.

    Security choice:
    The backend defines this structure so the frontend only renders what the
    server allows. This is the core idea of server-driven UI.
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["travel_offer"]
    widget_id: str
    title: str
    destination: str
    price: str
    description: str
    actions: list[TravelOfferAction]


def build_travel_offer_widget(
    *,
    widget_id: str,
    title: str,
    destination: str,
    price: str,
    description: str,
) -> TravelOfferWidget:
    """Build one beginner-friendly travel offer widget."""

    return TravelOfferWidget(
        type=TRAVEL_OFFER_WIDGET_TYPE,
        widget_id=widget_id,
        title=title,
        destination=destination,
        price=price,
        description=description,
        actions=[
            TravelOfferAction(
                type=BOOK_NOW_ACTION_TYPE,
                label="Book Now",
                payload=TravelOfferActionPayload(offer_id=widget_id),
            )
        ],
    )
