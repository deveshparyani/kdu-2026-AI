"""Mock backend data source for the Phase 2 safety demo."""

from __future__ import annotations


def get_user_data() -> dict[str, str]:
    """Return pretend customer profile data from a backend system."""
    return {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1-555-123-4567",
        "ssn": "123-45-6789",
    }
