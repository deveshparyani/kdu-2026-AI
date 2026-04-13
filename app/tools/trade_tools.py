from datetime import datetime, timezone

from langchain_core.tools import tool

from app.schema.trade_schema import ProposedTradeSchema, TradeResultSchema


def _now_utc_iso() -> str:
    """Return a simple UTC timestamp for transaction history."""
    return datetime.now(timezone.utc).isoformat()


@tool
def execute_trade(
    proposed_trade: dict,
    portfolio: dict[str, int],
    transactions: list[dict],
) -> dict:
    """Execute a simulated trade and return updated portfolio data."""
    trade = ProposedTradeSchema.model_validate(proposed_trade)

    portfolio_copy = dict(portfolio)
    transactions_copy = list(transactions)
    stock = trade.stock.strip().upper()

    if trade.quantity <= 0:
        trade_result = TradeResultSchema(
            status="invalid",
            action=trade.action,
            stock=stock,
            quantity=trade.quantity,
            unit_price=trade.unit_price,
            total_value=trade.total_value,
            message="Trade quantity must be greater than 0.",
        )
        return {
            "portfolio": portfolio_copy,
            "transactions": transactions_copy,
            "trade_result": trade_result.model_dump(),
        }

    if trade.action == "buy":
        portfolio_copy[stock] = portfolio_copy.get(stock, 0) + trade.quantity
        message = (
            f"Bought {trade.quantity} shares of {stock} at "
            f"{trade.unit_price:.2f} {trade.currency} each."
        )
    else:
        owned_quantity = portfolio_copy.get(stock, 0)
        if owned_quantity < trade.quantity:
            trade_result = TradeResultSchema(
                status="invalid",
                action=trade.action,
                stock=stock,
                quantity=trade.quantity,
                unit_price=trade.unit_price,
                total_value=trade.total_value,
                message=(
                    f"Cannot sell {trade.quantity} shares of {stock}. "
                    f"You only own {owned_quantity}."
                ),
            )
            return {
                "portfolio": portfolio_copy,
                "transactions": transactions_copy,
                "trade_result": trade_result.model_dump(),
            }

        remaining_quantity = owned_quantity - trade.quantity
        if remaining_quantity == 0:
            portfolio_copy.pop(stock, None)
        else:
            portfolio_copy[stock] = remaining_quantity

        message = (
            f"Sold {trade.quantity} shares of {stock} at "
            f"{trade.unit_price:.2f} {trade.currency} each."
        )

    transactions_copy.append(
        {
            "action": trade.action,
            "stock": stock,
            "quantity": trade.quantity,
            "unit_price": trade.unit_price,
            "total_value": trade.total_value,
            "currency": trade.currency,
            "timestamp": _now_utc_iso(),
        }
    )

    trade_result = TradeResultSchema(
        status="executed",
        action=trade.action,
        stock=stock,
        quantity=trade.quantity,
        unit_price=trade.unit_price,
        total_value=trade.total_value,
        message=message,
    )

    return {
        "portfolio": portfolio_copy,
        "transactions": transactions_copy,
        "trade_result": trade_result.model_dump(),
    }
