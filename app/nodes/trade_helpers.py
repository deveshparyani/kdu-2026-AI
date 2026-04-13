from typing import Literal

from langsmith import traceable
from langgraph.types import Command, interrupt

from app.graph.state import ChatState
from app.schema.trade_schema import ProposedTradeSchema, TradeResultSchema
from app.tools.currency_tools import convert_usd_to_currency, normalize_currency_code
from app.tools.finnhub_tools import get_stock_price_from_finnhub
from app.tools.trade_tools import execute_trade

TradeAction = Literal["buy", "sell"]
PendingNode = Literal["buy_stock", "sell_stock"]


def _create_invalid_result(
    action: PendingNode,
    message: str,
    stock: str | None = None,
    quantity: int | None = None,
) -> dict:
    """Build a consistent invalid trade response."""
    return TradeResultSchema(
        status="invalid",
        action=action,
        stock=stock,
        quantity=quantity,
        unit_price=None,
        total_value=None,
        message=message,
    ).model_dump()


def _create_rejected_result(proposed_trade: dict) -> dict:
    """Build a response for a user-rejected trade."""
    trade = ProposedTradeSchema.model_validate(proposed_trade)
    return TradeResultSchema(
        status="rejected",
        action=trade.action,
        stock=trade.stock,
        quantity=trade.quantity,
        unit_price=trade.unit_price,
        total_value=trade.total_value,
        message=(
            f"The {trade.action} trade for {trade.quantity} shares of "
            f"{trade.stock} was cancelled by the user."
        ),
    ).model_dump()


def _normalize_yes_no_reply(reply: object) -> str:
    """Normalize the resume value from the human approval step."""
    if isinstance(reply, dict):
        reply = reply.get("approval") or reply.get("answer") or reply.get("response")

    return str(reply or "").strip().lower()


def _make_confirmation_payload(proposed_trade: dict) -> dict:
    """Create the interrupt payload shown to the user."""
    trade = ProposedTradeSchema.model_validate(proposed_trade)
    return {
        "action": trade.action,
        "stock": trade.stock,
        "quantity": trade.quantity,
        "unit_price": trade.unit_price,
        "total_value": trade.total_value,
        "currency": trade.currency,
        "message": (
            f"Please confirm this trade: {trade.action} {trade.quantity} shares of "
            f"{trade.stock} at {trade.unit_price:.2f} {trade.currency} each "
            f"for an estimated total of {trade.total_value:.2f} {trade.currency}. "
            f"Reply with yes or no."
        ),
    }


@traceable(run_type="chain", name="build_proposed_trade")
def _build_proposed_trade(state: ChatState, action: TradeAction) -> tuple[dict, dict[str, float]]:
    """Validate the trade request and create the trade preview."""
    stock = (state.get("stock") or "").strip().upper()
    quantity = state.get("quantity")
    currency = normalize_currency_code(state.get("currency", "USD"))

    if not stock:
        raise ValueError("Stock symbol is required.")

    if quantity is None:
        raise ValueError("Quantity is required.")

    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0.")

    portfolio = state.get("portfolio", {})
    if action == "sell":
        owned_quantity = portfolio.get(stock, 0)
        if owned_quantity == 0:
            raise ValueError(f"You do not own any shares of {stock}.")
        if quantity > owned_quantity:
            raise ValueError(
                f"Cannot sell {quantity} shares of {stock}. You only own {owned_quantity}."
            )

    unit_price_usd = get_stock_price_from_finnhub.invoke({"symbol": stock})
    unit_price = convert_usd_to_currency.invoke(
        {
            "amount": unit_price_usd,
            "target_currency": currency,
        }
    )
    total_value = round(unit_price * quantity, 2)

    proposed_trade = ProposedTradeSchema(
        action=action,
        stock=stock,
        quantity=quantity,
        unit_price=unit_price,
        total_value=total_value,
        currency=currency,
    ).model_dump()

    updated_stock_prices = dict(state.get("stock_prices", {}))
    updated_stock_prices[stock] = unit_price

    return proposed_trade, updated_stock_prices


@traceable(run_type="chain", name="process_trade_node")
def process_trade_node(
    state: ChatState,
    *,
    action: TradeAction,
    node_name: PendingNode,
) -> ChatState | Command:
    """
    Shared trade flow for buy and sell nodes.

    Step 1: validate and cache the proposed trade in state
    Step 2: interrupt for human confirmation
    Step 3: resume and either execute or reject
    """
    cached_trade = state.get("proposed_trade")

    if not cached_trade or state.get("pending_action") != node_name:
        try:
            proposed_trade, updated_stock_prices = _build_proposed_trade(state, action)
        except ValueError as exc:
            return {
                "pending_action": None,
                "proposed_trade": {},
                "trade_result": _create_invalid_result(
                    node_name,
                    str(exc),
                    stock=state.get("stock"),
                    quantity=state.get("quantity"),
                ),
            }

        return Command(
            update={
                "pending_action": node_name,
                "proposed_trade": proposed_trade,
                "stock_prices": updated_stock_prices,
            },
            goto=node_name,
        )

    approval = interrupt(_make_confirmation_payload(cached_trade))
    normalized_reply = _normalize_yes_no_reply(approval)

    if normalized_reply != "yes":
        return {
            "pending_action": None,
            "proposed_trade": {},
            "trade_result": _create_rejected_result(cached_trade),
        }

    execution_result = execute_trade.invoke(
        {
            "proposed_trade": cached_trade,
            "portfolio": state.get("portfolio", {}),
            "transactions": state.get("transactions", []),
        }
    )

    return {
        "portfolio": execution_result["portfolio"],
        "transactions": execution_result["transactions"],
        "trade_result": execution_result["trade_result"],
        "pending_action": None,
        "proposed_trade": {},
    }
