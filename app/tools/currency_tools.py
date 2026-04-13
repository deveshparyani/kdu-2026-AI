import json
from pathlib import Path

from langchain_core.tools import tool


RATES_FILE = Path(__file__).resolve().parent.parent / "data" / "mock_exchange_rates.json"


def normalize_currency_code(currency: str | None) -> str:
    """Normalize currency names into supported uppercase codes."""
    normalized = (currency or "USD").strip().upper()

    currency_aliases = {
        "USD": "USD",
        "DOLLAR": "USD",
        "DOLLARS": "USD",
        "US DOLLAR": "USD",
        "US DOLLARS": "USD",
        "INR": "INR",
        "RUPEE": "INR",
        "RUPEES": "INR",
        "INDIAN RUPEE": "INR",
        "INDIAN RUPEES": "INR",
        "EUR": "EUR",
        "EURO": "EUR",
        "EUROS": "EUR",
    }

    return currency_aliases.get(normalized, normalized)


def load_mock_exchange_rates() -> dict:
    """Load mock exchange-rate data from the JSON file."""
    with RATES_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


@tool
def convert_usd_to_currency(amount: float, target_currency: str) -> float:
    """Convert a USD amount into the requested currency using mock JSON data."""
    data = load_mock_exchange_rates()
    normalized_currency = normalize_currency_code(target_currency)
    rates = data.get("rates", {})

    if normalized_currency not in rates:
        raise ValueError(f"Unsupported currency: {normalized_currency}")

    converted_amount = amount * rates[normalized_currency]
    return round(converted_amount, 2)
