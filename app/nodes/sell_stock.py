from app.graph.state import ChatState
from app.nodes.trade_helpers import process_trade_node


def sell_stock(state: ChatState):
    """Validate, confirm, and execute a sell trade."""
    return process_trade_node(
        state,
        action="sell",
        node_name="sell_stock",
    )
