from app.graph.state import ChatState
from app.schema.read_only_schema import TransactionHistorySchema


def get_transactions(state: ChatState) -> ChatState:
    """Return transaction history from state in a fixed JSON format."""
    transactions = list(state.get("transactions", []))

    if not transactions:
        response = TransactionHistorySchema(
            count=0,
            transactions=[],
            message="No transactions found.",
        )
    else:
        response = TransactionHistorySchema(
            count=len(transactions),
            transactions=transactions,
            message=f"Found {len(transactions)} transactions.",
        )

    return {
        "transaction_history": response.model_dump(),
    }
