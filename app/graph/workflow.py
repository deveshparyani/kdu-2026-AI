from langsmith import traceable
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.state import ChatState
from app.nodes.buy_stock import buy_stock
from app.nodes.fetch_stock_price import fetch_stock_price
from app.nodes.get_portfolio_details import get_portfolio_details
from app.nodes.get_transactions import get_transactions
from app.nodes.parse_input import parse_input
from app.nodes.sell_stock import sell_stock
from app.nodes.unknown import unknown


def finish_request(state: ChatState) -> ChatState:
    """Fallback node for requests that are not implemented yet."""
    return state


@traceable(run_type="chain", name="route_after_parse")
def route_after_parse(state: ChatState) -> str:
    """Choose the next node based on the parsed user intent."""
    intent = state.get("intent")

    if intent == "get_portfolio":
        return "get_portfolio_details"
    if intent == "get_transactions":
        return "get_transactions"
    if intent == "get_stock_price":
        return "fetch_stock_price"
    if intent == "buy_stock":
        return "buy_stock"
    if intent == "sell_stock":
        return "sell_stock"
    if intent == "unknown":
        return "unknown"

    return "finish_request"


def build_stock_trading_graph():
    """Build the LangGraph workflow for the stock trading assistant."""
    workflow = StateGraph(ChatState)

    workflow.add_node("parse_input", parse_input)
    workflow.add_node("get_portfolio_details", get_portfolio_details)
    workflow.add_node("get_transactions", get_transactions)
    workflow.add_node("fetch_stock_price", fetch_stock_price)
    workflow.add_node("buy_stock", buy_stock)
    workflow.add_node("sell_stock", sell_stock)
    workflow.add_node("unknown", unknown)
    workflow.add_node("finish_request", finish_request)

    workflow.add_edge(START, "parse_input")
    workflow.add_conditional_edges("parse_input", route_after_parse)
    workflow.add_edge("get_portfolio_details", END)
    workflow.add_edge("get_transactions", END)
    workflow.add_edge("fetch_stock_price", END)
    workflow.add_edge("buy_stock", END)
    workflow.add_edge("sell_stock", END)
    workflow.add_edge("unknown", END)
    workflow.add_edge("finish_request", END)

    return workflow


checkpointer = MemorySaver()
stock_trading_graph = build_stock_trading_graph().compile(checkpointer=checkpointer)
