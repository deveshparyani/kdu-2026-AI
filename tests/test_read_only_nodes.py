import unittest
from types import SimpleNamespace

from app.graph.workflow import route_after_parse
from app.nodes.fetch_stock_price import fetch_stock_price
from app.nodes.get_transactions import get_transactions
import app.nodes.fetch_stock_price as fetch_stock_price_module


class ReadOnlyNodeTests(unittest.TestCase):
    def setUp(self):
        self.original_price_tool = fetch_stock_price_module.get_stock_price_from_finnhub

    def tearDown(self):
        fetch_stock_price_module.get_stock_price_from_finnhub = self.original_price_tool

    def test_get_transactions_returns_empty_history(self):
        result = get_transactions({"transactions": []})

        self.assertEqual(result["transaction_history"]["count"], 0)
        self.assertEqual(result["transaction_history"]["transactions"], [])
        self.assertEqual(
            result["transaction_history"]["message"],
            "No transactions found.",
        )

    def test_get_transactions_returns_stored_history(self):
        transactions = [
            {
                "action": "buy",
                "stock": "AAPL",
                "quantity": 2,
                "unit_price": 120.0,
                "total_value": 240.0,
                "currency": "USD",
                "timestamp": "2026-04-13T10:00:00+00:00",
            },
            {
                "action": "sell",
                "stock": "TSLA",
                "quantity": 1,
                "unit_price": 180.0,
                "total_value": 180.0,
                "currency": "USD",
                "timestamp": "2026-04-13T11:00:00+00:00",
            },
        ]

        result = get_transactions({"transactions": transactions})

        self.assertEqual(result["transaction_history"]["count"], 2)
        self.assertEqual(result["transaction_history"]["transactions"], transactions)
        self.assertEqual(
            result["transaction_history"]["message"],
            "Found 2 transactions.",
        )

    def test_fetch_stock_price_returns_price_when_tool_succeeds(self):
        fetch_stock_price_module.get_stock_price_from_finnhub = SimpleNamespace(
            invoke=lambda payload: 212.45
        )

        result = fetch_stock_price({"stock": "AAPL", "currency": "USD"})

        self.assertEqual(result["stock_prices"]["AAPL"], 212.45)
        self.assertEqual(result["stock_price_response"]["stock"], "AAPL")
        self.assertEqual(result["stock_price_response"]["current_price"], 212.45)
        self.assertIn("AAPL", result["stock_price_response"]["message"])

    def test_fetch_stock_price_converts_price_to_requested_currency(self):
        fetch_stock_price_module.get_stock_price_from_finnhub = SimpleNamespace(
            invoke=lambda payload: 10.0
        )

        result = fetch_stock_price({"stock": "AAPL", "currency": "INR"})

        self.assertEqual(result["stock_prices"]["AAPL"], 832.5)
        self.assertEqual(result["stock_price_response"]["currency"], "INR")
        self.assertEqual(result["stock_price_response"]["current_price"], 832.5)

    def test_fetch_stock_price_handles_missing_stock(self):
        result = fetch_stock_price({"currency": "USD"})

        self.assertEqual(result["stock_price_response"]["stock"], "")
        self.assertEqual(result["stock_price_response"]["current_price"], None)
        self.assertIn("Stock symbol is required", result["stock_price_response"]["message"])

    def test_fetch_stock_price_handles_tool_failure(self):
        def raise_error(payload):
            raise ValueError("Finnhub error")

        fetch_stock_price_module.get_stock_price_from_finnhub = SimpleNamespace(
            invoke=raise_error
        )

        result = fetch_stock_price({"stock": "AAPL", "currency": "USD"})

        self.assertEqual(result["stock_price_response"]["stock"], "AAPL")
        self.assertEqual(result["stock_price_response"]["current_price"], None)
        self.assertIn("Could not fetch the stock price", result["stock_price_response"]["message"])

    def test_route_after_parse_handles_transactions(self):
        self.assertEqual(
            route_after_parse({"intent": "get_transactions"}),
            "get_transactions",
        )

    def test_route_after_parse_handles_stock_price(self):
        self.assertEqual(
            route_after_parse({"intent": "get_stock_price"}),
            "fetch_stock_price",
        )


if __name__ == "__main__":
    unittest.main()
