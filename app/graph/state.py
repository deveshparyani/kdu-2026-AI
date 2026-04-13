from typing import Any, Optional, TypedDict

class ChatState(TypedDict, total=False):
    user_query: str

    intent: Optional[str]
    stock: Optional[str]
    quantity: Optional[int]
    amount: Optional[float]

    portfolio: dict[str, int]

    currency: str

    pending_action: Optional[str]
    proposed_trade: dict[str, Any]
    trade_result: dict[str, Any]

    stock_prices: dict[str, float]
    portfolio_value: float
    portfolio_details: dict[str, Any]
    stock_price_response: dict[str, Any]
    assistant_response: str
    observability: dict[str, Any]

    transactions: list[dict]
    transaction_history: dict[str, Any]
    parse_error: Optional[str]
