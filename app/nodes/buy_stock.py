from app.graph.state import ChatState
from app.nodes.trade_helpers import process_trade_node


def buy_stock(state: ChatState):
    """Validate, confirm, and execute a buy trade."""
    return process_trade_node(
        state,
        action="buy",
        node_name="buy_stock",
    )
