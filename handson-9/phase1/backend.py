"""Mock backend service for the prompt-injection demo."""


def get_user_data() -> dict[str, str]:
    """Return pretend customer data that should be treated as sensitive."""
    return {
        "name": "John Doe",
        "email": "john@example.com",
        "ssn": "123-45-6789",
    }
