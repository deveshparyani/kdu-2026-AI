import os

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

FINNHUB_QUOTE_URL = "https://finnhub.io/api/v1/quote"


@tool
def get_stock_price_from_finnhub(symbol: str) -> float:
    """Get the latest stock price for a symbol using Finnhub."""
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        raise ValueError(
            "FINNHUB_API_KEY is missing. Add it to your .env file before using this tool."
        )

    response = requests.get(
        FINNHUB_QUOTE_URL,
        params={"symbol": symbol, "token": api_key},
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()
    current_price = data.get("c")

    if current_price in (None, 0):
        raise ValueError(f"Could not get a valid current price for {symbol}.")

    return float(current_price)
