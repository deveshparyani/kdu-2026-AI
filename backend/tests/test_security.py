"""Why this file exists: it tests thread ownership, widget actions, and handoff behavior."""

import pytest
from fastapi.testclient import TestClient

from app.db import reset_store
from app.main import app


@pytest.fixture(autouse=True)
def clear_store() -> None:
    """Start each test with empty in-memory users, threads, and messages."""

    reset_store()


@pytest.fixture
def client() -> TestClient:
    """Return one FastAPI test client."""

    return TestClient(app)


def create_session(client: TestClient, user_id: str) -> dict:
    """Helper that creates one chat session and returns the JSON payload."""

    response = client.post(
        "/api/chat/session",
        headers={"X-Demo-User-Id": user_id},
        json={},
    )
    assert response.status_code == 200
    return response.json()


def test_user_a_can_create_a_thread(client: TestClient) -> None:
    payload = create_session(client, "user_a")

    assert payload["user_id"] == "user_a"
    assert payload["thread_id"].startswith("thread_")
    assert payload["client_secret"].startswith("cs_")
    assert payload["mode"] == "ai"
    assert payload["messages"][0]["role"] == "assistant"


def test_user_a_can_continue_their_own_thread(client: TestClient) -> None:
    first_payload = create_session(client, "user_a")
    thread_id = first_payload["thread_id"]

    second_response = client.post(
        "/api/chat/session",
        headers={"X-Demo-User-Id": "user_a"},
        json={"thread_id": thread_id},
    )

    assert second_response.status_code == 200
    payload = second_response.json()

    assert payload["user_id"] == "user_a"
    assert payload["thread_id"] == thread_id


def test_user_b_cannot_access_user_as_thread(client: TestClient) -> None:
    first_payload = create_session(client, "user_a")
    thread_id = first_payload["thread_id"]

    attack_response = client.post(
        "/api/chat/session",
        headers={"X-Demo-User-Id": "user_b"},
        json={"thread_id": thread_id},
    )

    assert attack_response.status_code == 403
    assert "cross-user thread access" in attack_response.json()["detail"]


def test_threads_returns_only_owned_threads(client: TestClient) -> None:
    user_a_thread_one = create_session(client, "user_a")["thread_id"]
    user_a_thread_two = create_session(client, "user_a")["thread_id"]
    _ = create_session(client, "user_b")

    response = client.get(
        "/api/threads",
        headers={"X-Demo-User-Id": "user_a"},
    )

    assert response.status_code == 200
    payload = response.json()
    thread_ids = {thread["thread_id"] for thread in payload["threads"]}
    user_ids = {thread["user_id"] for thread in payload["threads"]}

    assert thread_ids == {user_a_thread_one, user_a_thread_two}
    assert user_ids == {"user_a"}


def test_chat_message_returns_assistant_reply_and_widget(client: TestClient) -> None:
    session_payload = create_session(client, "user_a")

    response = client.post(
        "/api/chat/message",
        headers={"X-Demo-User-Id": "user_a"},
        json={
            "thread_id": session_payload["thread_id"],
            "message": "Find me a weekend trip to Goa under 10000"
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"]["role"] == "assistant"
    assert payload["assistant_message"]["widgets"][0]["type"] == "travel_offer"


def test_book_now_action_succeeds_for_thread_owner(client: TestClient) -> None:
    session_payload = create_session(client, "user_a")
    thread_id = session_payload["thread_id"]

    action_response = client.post(
        "/api/chat/action",
        headers={"X-Demo-User-Id": "user_a"},
        json={
            "thread_id": thread_id,
            "widget_id": "offer_goa_001",
            "action_type": "book_now",
            "payload": {"offer_id": "offer_goa_001"},
            "idempotency_key": "idem-booking-001",
        },
    )

    assert action_response.status_code == 200
    payload = action_response.json()
    assert payload["status"] == "success"
    assert payload["message"] == "Booking started for offer_goa_001"
    assert "booking flow for Weekend Trip to Goa" in payload["assistant_message"]["content"]


def test_book_now_action_rejects_cross_user_thread_access(client: TestClient) -> None:
    thread_id = create_session(client, "user_a")["thread_id"]

    attack_response = client.post(
        "/api/chat/action",
        headers={"X-Demo-User-Id": "user_b"},
        json={
            "thread_id": thread_id,
            "widget_id": "offer_goa_001",
            "action_type": "book_now",
            "payload": {"offer_id": "offer_goa_001"},
            "idempotency_key": "idem-booking-002",
        },
    )

    assert attack_response.status_code == 403


def test_book_now_action_is_idempotent(client: TestClient) -> None:
    thread_id = create_session(client, "user_a")["thread_id"]
    payload = {
        "thread_id": thread_id,
        "widget_id": "offer_goa_001",
        "action_type": "book_now",
        "payload": {"offer_id": "offer_goa_001"},
        "idempotency_key": "idem-booking-003",
    }

    first_response = client.post(
        "/api/chat/action",
        headers={"X-Demo-User-Id": "user_a"},
        json=payload,
    )
    second_response = client.post(
        "/api/chat/action",
        headers={"X-Demo-User-Id": "user_a"},
        json=payload,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()


def test_thread_mode_starts_as_ai(client: TestClient) -> None:
    thread_id = create_session(client, "user_a")["thread_id"]

    mode_response = client.get(
        f"/api/threads/{thread_id}/mode",
        headers={"X-Demo-User-Id": "user_a"},
    )

    assert mode_response.status_code == 200
    assert mode_response.json() == {"mode": "ai"}


def test_user_can_start_and_end_human_handoff(client: TestClient) -> None:
    thread_id = create_session(client, "user_a")["thread_id"]

    start_response = client.post(
        f"/api/threads/{thread_id}/handoff/start",
        headers={"X-Demo-User-Id": "user_a"},
    )
    end_response = client.post(
        f"/api/threads/{thread_id}/handoff/end",
        headers={"X-Demo-User-Id": "user_a"},
    )

    assert start_response.status_code == 200
    assert start_response.json() == {
        "mode": "human",
        "message": "Human handoff started. AI responses are paused.",
    }
    assert end_response.status_code == 200
    assert end_response.json() == {
        "mode": "ai",
        "message": "AI responses resumed.",
    }


def test_chat_message_returns_paused_text_in_human_mode(client: TestClient) -> None:
    thread_id = create_session(client, "user_a")["thread_id"]

    _ = client.post(
        f"/api/threads/{thread_id}/handoff/start",
        headers={"X-Demo-User-Id": "user_a"},
    )

    response = client.post(
        "/api/chat/message",
        headers={"X-Demo-User-Id": "user_a"},
        json={
            "thread_id": thread_id,
            "message": "Can you book that now?"
        },
    )

    assert response.status_code == 200
    assert (
        response.json()["assistant_message"]["content"]
        == "A human agent has taken over this conversation. AI responses are paused."
    )


def test_handoff_rejects_cross_user_thread_access(client: TestClient) -> None:
    thread_id = create_session(client, "user_a")["thread_id"]

    attack_response = client.post(
        f"/api/threads/{thread_id}/handoff/start",
        headers={"X-Demo-User-Id": "user_b"},
    )

    assert attack_response.status_code == 403
