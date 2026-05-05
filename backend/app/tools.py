"""Why this file exists: it contains small travel helper functions for the demo app."""

from .widgets import TravelOfferWidget, build_travel_offer_widget


TRAVEL_KEYWORDS = {
    "trip",
    "travel",
    "flight",
    "hotel",
    "booking",
    "book",
    "weekend",
    "goa",
    "budget",
    "vacation",
    "holiday",
}

ALL_DEMO_WIDGETS = [
    build_travel_offer_widget(
        widget_id="offer_goa_001",
        title="Weekend Trip to Goa",
        destination="Goa",
        price="₹7,500",
        description="Round trip flight + 2 nights hotel",
    ),
    build_travel_offer_widget(
        widget_id="offer_goa_002",
        title="Budget Beach Escape in Goa",
        destination="Goa",
        price="₹9,800",
        description="Night bus + 2 nights guest house near Baga Beach",
    ),
    build_travel_offer_widget(
        widget_id="offer_kerala_001",
        title="Backwater Escape in Kerala",
        destination="Kerala",
        price="₹9,200",
        description="Train tickets + 2 nights houseboat stay",
    ),
]


def looks_like_travel_request(message: str) -> bool:
    """Return True when the user message sounds like a travel search."""

    text = message.lower()
    return any(keyword in text for keyword in TRAVEL_KEYWORDS)


def search_demo_travel_offers(query: str = "") -> list[TravelOfferWidget]:
    """
    Return server-defined travel widgets for the current user request.

    Security choice:
    The backend, not the browser, decides which widget structure exists and
    which actions are attached to it.
    """

    text = query.lower().strip()
    if "kerala" in text or "nature" in text:
        return [ALL_DEMO_WIDGETS[2]]
    if "budget" in text and "goa" in text:
        return [ALL_DEMO_WIDGETS[1]]
    if "goa" in text or "weekend" in text or "beach" in text:
        return [ALL_DEMO_WIDGETS[0]]

    return [ALL_DEMO_WIDGETS[0]]


def get_demo_widget_by_id(widget_id: str) -> TravelOfferWidget | None:
    """Find one known widget definition by id."""

    for widget in ALL_DEMO_WIDGETS:
        if widget.widget_id == widget_id:
            return widget
    return None


def split_text_for_stream(text: str, chunk_size: int = 18) -> list[str]:
    """
    Split text into short chunks for simulated streaming.

    This is a simple fallback that feels like real-time output without requiring
    a full provider streaming integration on day one.
    """

    chunks: list[str] = []
    start_index = 0
    while start_index < len(text):
        chunks.append(text[start_index : start_index + chunk_size])
        start_index += chunk_size
    return chunks or [""]
