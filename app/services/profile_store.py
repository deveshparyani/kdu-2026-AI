import re

from app.db.models import UserProfile
from app.db.session import get_db_session


# This function cleans the raw matched location text before saving it.
def clean_location_text(location: str) -> str:
    cleaned_location = location.strip(" .,!?:;")
    stop_words = {"today", "tomorrow", "now", "please", "currently"}
    parts = cleaned_location.split()

    while parts and parts[-1].lower() in stop_words:
        parts.pop()

    return " ".join(parts).title()


# This function finds a location in more natural user sentences.
def extract_location_from_message(message: str) -> str | None:
    patterns = [
        r"my favorite city is ([a-zA-Z ]+)",
        r"i love ([a-zA-Z ]+)",
        r"i like ([a-zA-Z ]+)",
        r"my city is ([a-zA-Z ]+)",
        r"my hometown is ([a-zA-Z ]+)",
        r"i live in ([a-zA-Z ]+)",
        r"i stay in ([a-zA-Z ]+)",
        r"i am based in ([a-zA-Z ]+)",
        r"i'm based in ([a-zA-Z ]+)",
        r"i am from ([a-zA-Z ]+)",
        r"i'm from ([a-zA-Z ]+)",
        r"my location is ([a-zA-Z ]+)",
        r"use ([a-zA-Z ]+) for weather",
        r"weather in ([a-zA-Z ]+)",
        r"weather for ([a-zA-Z ]+)",
        r"temperature in ([a-zA-Z ]+)",
        r"forecast for ([a-zA-Z ]+)",
    ]

    cleaned_message = message.strip().lower()

    for pattern in patterns:
        match = re.search(pattern, cleaned_message)
        if match:
            location = clean_location_text(match.group(1))
            if location:
                return location

    return None


# This function finds a place reference in general city or place questions.
def extract_place_reference_from_message(message: str) -> str | None:
    patterns = [
        r"current place in conversation: ([a-zA-Z ]+)",
        r"tell me about ([a-zA-Z ]+)",
        r"about ([a-zA-Z ]+)",
        r"what is ([a-zA-Z ]+)",
        r"what about ([a-zA-Z ]+)",
        r"where is ([a-zA-Z ]+)",
        r"where is ([a-zA-Z ]+) located",
    ]
    ignored_terms = {
        "ai",
        "artificial intelligence",
        "weather",
        "temperature",
        "forecast",
        "hello",
    }
    cleaned_message = message.strip().lower()

    for pattern in patterns:
        match = re.search(pattern, cleaned_message)
        if match:
            place = clean_location_text(match.group(1))
            if place and place.lower() not in ignored_terms:
                return place

    return None


# This function looks through recent thread messages and finds the latest user-mentioned location.
def extract_location_from_thread(thread_messages: list[dict[str, str]]) -> str | None:
    for message in reversed(thread_messages):
        role = message.get("role", "")
        content = message.get("content", "")

        if role != "user":
            continue

        location = extract_location_from_message(content)
        if location:
            return location

        place = extract_place_reference_from_message(content)
        if place:
            return place

    return None


# This function reads one user's saved profile from the database.
def get_user_profile(user_id: str) -> UserProfile | None:
    session = get_db_session()

    try:
        return session.get(UserProfile, user_id)
    finally:
        session.close()


# This function creates or updates the user's saved profile in the database.
def save_user_profile(
    user_id: str,
    preferred_location: str | None = None,
    preferred_style: str | None = None,
) -> UserProfile:
    session = get_db_session()

    try:
        profile = session.get(UserProfile, user_id)

        if profile is None:
            profile = UserProfile(user_id=user_id)
            session.add(profile)

        if preferred_location:
            profile.preferred_location = preferred_location

        if preferred_style:
            profile.preferred_style = preferred_style

        session.commit()
        session.refresh(profile)
        return profile
    finally:
        session.close()


# This function updates long-term profile memory based on the current user message.
def update_profile_from_message(
    user_id: str,
    message: str,
    style: str,
) -> tuple[UserProfile | None, bool]:
    location = extract_location_from_message(message)
    preferred_style = style if style != "default" else None

    existing_profile = get_user_profile(user_id)
    old_location = existing_profile.preferred_location if existing_profile else None
    old_style = existing_profile.preferred_style if existing_profile else None

    if location is None and preferred_style is None:
        return existing_profile, False

    profile = save_user_profile(
        user_id=user_id,
        preferred_location=location or old_location,
        preferred_style=preferred_style or old_style,
    )

    profile_updated = (
        profile.preferred_location != old_location
        or profile.preferred_style != old_style
    )

    return profile, profile_updated
