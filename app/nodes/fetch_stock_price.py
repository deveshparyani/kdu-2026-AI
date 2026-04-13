from app.graph.state import ChatState
from app.schema.read_only_schema import StockPriceResponseSchema
from app.tools.currency_tools import convert_usd_to_currency, normalize_currency_code
from app.tools.finnhub_tools import get_stock_price_from_finnhub


def fetch_stock_price(state: ChatState) -> ChatState:
    """Fetch the current stock price and return it in a fixed JSON format."""
    stock = (state.get("stock") or "").strip().upper()
    currency = normalize_currency_code(state.get("currency", "USD"))

    if not stock:
        response = StockPriceResponseSchema(
            stock="",
            current_price=None,
            currency=currency,
            message="Stock symbol is required to fetch the stock price.",
        )
        return {
            "stock_price_response": response.model_dump(),
        }

    try:
        current_price_usd = get_stock_price_from_finnhub.invoke({"symbol": stock})
        current_price = convert_usd_to_currency.invoke(
            {
                "amount": current_price_usd,
                "target_currency": currency,
            }
        )
    except Exception:
        response = StockPriceResponseSchema(
            stock=stock,
            current_price=None,
            currency=currency,
            message=f"Could not fetch the stock price for {stock}.",
        )
        return {
            "stock_price_response": response.model_dump(),
        }

    response = StockPriceResponseSchema(
        stock=stock,
        current_price=current_price,
        currency=currency,
        message=f"The current price of {stock} is {current_price:.2f} {currency}.",
    )

    updated_stock_prices = dict(state.get("stock_prices", {}))
    updated_stock_prices[stock] = current_price

    return {
        "stock_prices": updated_stock_prices,
        "stock_price_response": response.model_dump(),
    }
