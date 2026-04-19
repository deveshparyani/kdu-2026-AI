from app.services.llm_client import LLMClient


def test_classifier_handles_faq_query() -> None:
    client = LLMClient()
    result = client.classify_query("What are your hours?", model_name="cheap")

    assert result["classification"] == {
        "category": "FAQ",
        "complexity": "low",
        "response_type": "simple",
    }


def test_classifier_handles_booking_query() -> None:
    client = LLMClient()
    result = client.classify_query(
        "Can I reschedule my cleaning appointment?",
        model_name="cheap",
    )

    assert result["classification"] == {
        "category": "booking",
        "complexity": "medium",
        "response_type": "standard",
    }


def test_classifier_handles_complaint_query() -> None:
    client = LLMClient()
    result = client.classify_query(
        "My plumber didn't show up and I need a refund",
        model_name="cheap",
    )

    assert result["classification"] == {
        "category": "complaint",
        "complexity": "high",
        "response_type": "complex",
    }

