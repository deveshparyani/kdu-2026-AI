import unittest
from types import SimpleNamespace

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.graph.state import ChatState
from app.nodes.buy_stock import buy_stock
from app.nodes.sell_stock import sell_stock
from app.tools.trade_tools import execute_trade
import app.nodes.trade_helpers as trade_helpers


def build_single_node_graph(node_name: str, node_fn):
    """Build a tiny graph for testing one interrupting trade node."""
    workflow = StateGraph(ChatState)
    workflow.add_node(node_name, node_fn)
    workflow.add_edge(START, node_name)
    workflow.add_edge(node_name, END)
    return workflow.compile(checkpointer=MemorySaver())


class TradeFlowTests(unittest.TestCase):
    def setUp(self):
        self.original_price_tool = trade_helpers.get_stock_price_from_finnhub

    def tearDown(self):
        trade_helpers.get_stock_price_from_finnhub = self.original_price_tool

    def use_fake_price(self, price: float):
        """Replace the Finnhub tool with a tiny fake for tests."""
        trade_helpers.get_stock_price_from_finnhub = SimpleNamespace(
            invoke=lambda payload: price
        )

    def test_buy_validation_fails_when_stock_is_missing(self):
        result = buy_stock(
            {
                "quantity": 2,
                "portfolio": {},
                "currency": "USD",
                "transactions": [],
            }
        )

        self.assertEqual(result["trade_result"]["status"], "invalid")
        self.assertEqual(result["pending_action"], None)
        self.assertIn("Stock symbol is required", result["trade_result"]["message"])

    def test_buy_validation_fails_when_quantity_is_missing_zero_or_negative(self):
        for quantity in [None, 0, -1]:
            with self.subTest(quantity=quantity):
                state = {
                    "stock": "AAPL",
                    "portfolio": {},
                    "currency": "USD",
                    "transactions": [],
                }
                if quantity is not None:
                    state["quantity"] = quantity

                result = buy_stock(state)
                self.assertEqual(result["trade_result"]["status"], "invalid")

    def test_sell_validation_fails_when_stock_not_owned(self):
        result = sell_stock(
            {
                "stock": "AAPL",
                "quantity": 2,
                "portfolio": {},
                "currency": "USD",
                "transactions": [],
            }
        )

        self.assertEqual(result["trade_result"]["status"], "invalid")
        self.assertIn("do not own any shares", result["trade_result"]["message"])

    def test_sell_validation_fails_when_quantity_is_greater_than_owned(self):
        result = sell_stock(
            {
                "stock": "AAPL",
                "quantity": 5,
                "portfolio": {"AAPL": 2},
                "currency": "USD",
                "transactions": [],
            }
        )

        self.assertEqual(result["trade_result"]["status"], "invalid")
        self.assertIn("You only own 2", result["trade_result"]["message"])

    def test_buy_graph_interrupts_and_executes_on_yes(self):
        self.use_fake_price(123.45)
        graph = build_single_node_graph("buy_stock", buy_stock)
        config = {"configurable": {"thread_id": "buy-approval-thread"}}

        first_result = graph.invoke(
            {
                "stock": "AAPL",
                "quantity": 2,
                "portfolio": {},
                "currency": "USD",
                "transactions": [],
            },
            config=config,
        )

        self.assertIn("__interrupt__", first_result)
        interrupt_payload = first_result["__interrupt__"][0].value
        self.assertEqual(interrupt_payload["action"], "buy")
        self.assertEqual(interrupt_payload["stock"], "AAPL")
        self.assertEqual(interrupt_payload["quantity"], 2)
        self.assertEqual(interrupt_payload["unit_price"], 123.45)

        second_result = graph.invoke(Command(resume="yes"), config=config)

        self.assertEqual(second_result["trade_result"]["status"], "executed")
        self.assertEqual(second_result["portfolio"]["AAPL"], 2)
        self.assertEqual(len(second_result["transactions"]), 1)
        self.assertEqual(second_result["transactions"][0]["action"], "buy")
        self.assertEqual(second_result["pending_action"], None)

    def test_sell_graph_interrupts_and_rejects_on_no(self):
        self.use_fake_price(50.0)
        graph = build_single_node_graph("sell_stock", sell_stock)
        config = {"configurable": {"thread_id": "sell-reject-thread"}}

        first_result = graph.invoke(
            {
                "stock": "AAPL",
                "quantity": 2,
                "portfolio": {"AAPL": 2},
                "currency": "USD",
                "transactions": [],
            },
            config=config,
        )

        self.assertIn("__interrupt__", first_result)
        interrupt_payload = first_result["__interrupt__"][0].value
        self.assertEqual(interrupt_payload["action"], "sell")
        self.assertEqual(interrupt_payload["total_value"], 100.0)

        second_result = graph.invoke(Command(resume="no"), config=config)

        self.assertEqual(second_result["trade_result"]["status"], "rejected")
        self.assertEqual(second_result["portfolio"]["AAPL"], 2)
        self.assertEqual(second_result["transactions"], [])
        self.assertEqual(second_result["pending_action"], None)

    def test_sell_execution_removes_stock_when_quantity_reaches_zero(self):
        self.use_fake_price(75.0)
        graph = build_single_node_graph("sell_stock", sell_stock)
        config = {"configurable": {"thread_id": "sell-remove-thread"}}

        graph.invoke(
            {
                "stock": "AAPL",
                "quantity": 3,
                "portfolio": {"AAPL": 3},
                "currency": "USD",
                "transactions": [],
            },
            config=config,
        )
        result = graph.invoke(Command(resume="yes"), config=config)

        self.assertEqual(result["trade_result"]["status"], "executed")
        self.assertNotIn("AAPL", result["portfolio"])
        self.assertEqual(result["transactions"][0]["action"], "sell")

    def test_execute_trade_tool_returns_structured_result(self):
        result = execute_trade.invoke(
            {
                "proposed_trade": {
                    "action": "buy",
                    "stock": "AAPL",
                    "quantity": 1,
                    "unit_price": 200.0,
                    "total_value": 200.0,
                    "currency": "USD",
                },
                "portfolio": {},
                "transactions": [],
            }
        )

        self.assertEqual(result["trade_result"]["status"], "executed")
        self.assertEqual(result["trade_result"]["stock"], "AAPL")
        self.assertEqual(result["portfolio"]["AAPL"], 1)
        self.assertIn("Bought 1 shares of AAPL", result["trade_result"]["message"])


if __name__ == "__main__":
    unittest.main()
