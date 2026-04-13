import unittest
from types import SimpleNamespace

from app.nodes.get_portfolio_details import get_portfolio_details
from app.nodes.parse_input import parse_input
from app.schema.get_portfolio_details_schema import PortfolioDetailsSchema
from app.schema.parse_input_schema import ParseInputSchema
from app.tools.currency_tools import convert_usd_to_currency, normalize_currency_code
import app.nodes.get_portfolio_details as get_portfolio_details_module
import app.nodes.parse_input as parse_input_module


class CurrencyFeatureTests(unittest.TestCase):
    def setUp(self):
        self.original_parser = parse_input_module.structured_model
        self.original_price_tool = get_portfolio_details_module.get_stock_price_from_finnhub
        self.original_portfolio_model = get_portfolio_details_module.structured_model

    def tearDown(self):
        parse_input_module.structured_model = self.original_parser
        get_portfolio_details_module.get_stock_price_from_finnhub = self.original_price_tool
        get_portfolio_details_module.structured_model = self.original_portfolio_model

    def test_parse_input_sets_requested_currency(self):
        parse_input_module.structured_model = SimpleNamespace(
            invoke=lambda messages: {
                "raw": SimpleNamespace(
                    usage_metadata={
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "total_tokens": 15,
                    }
                ),
                "parsed": ParseInputSchema(
                    intent="get_stock_price",
                    stock="AAPL",
                    quantity=None,
                    amount=None,
                    currency="euro",
                ),
            }
        )

        result = parse_input({}, "tell me apple stock price in euro")

        self.assertEqual(result["currency"], "EUR")
        self.assertEqual(result["stock"], "AAPL")
        self.assertEqual(result["intent"], "get_stock_price")

    def test_parse_input_keeps_existing_currency_when_not_asked(self):
        parse_input_module.structured_model = SimpleNamespace(
            invoke=lambda messages: {
                "raw": SimpleNamespace(
                    usage_metadata={
                        "input_tokens": 8,
                        "output_tokens": 4,
                        "total_tokens": 12,
                    }
                ),
                "parsed": ParseInputSchema(
                    intent="get_portfolio",
                    stock=None,
                    quantity=None,
                    amount=None,
                    currency=None,
                ),
            }
        )

        result = parse_input({"currency": "INR"}, "show my portfolio")

        self.assertEqual(result["currency"], "INR")

    def test_convert_usd_to_currency_uses_mock_json(self):
        self.assertEqual(
            convert_usd_to_currency.invoke({"amount": 10.0, "target_currency": "INR"}),
            832.5,
        )
        self.assertEqual(
            convert_usd_to_currency.invoke({"amount": 10.0, "target_currency": "EURO"}),
            9.2,
        )

    def test_normalize_currency_code_handles_common_names(self):
        self.assertEqual(normalize_currency_code("euro"), "EUR")
        self.assertEqual(normalize_currency_code("rupees"), "INR")
        self.assertEqual(normalize_currency_code("usd"), "USD")

    def test_get_portfolio_details_converts_prices_to_requested_currency(self):
        get_portfolio_details_module.get_stock_price_from_finnhub = SimpleNamespace(
            invoke=lambda payload: 10.0
        )
        get_portfolio_details_module.structured_model = SimpleNamespace(
            invoke=lambda messages: {
                "raw": SimpleNamespace(
                    usage_metadata={
                        "input_tokens": 20,
                        "output_tokens": 10,
                        "total_tokens": 30,
                    }
                ),
                "parsed": PortfolioDetailsSchema(
                    currency="INR",
                    total_portfolio_value=1665.0,
                    holdings=[
                        {
                            "stock": "AAPL",
                            "quantity": 2,
                            "current_price": 832.5,
                            "total_value": 1665.0,
                        }
                    ],
                    message="Your portfolio is worth 1665.00 INR.",
                ),
            }
        )

        result = get_portfolio_details(
            {
                "portfolio": {"AAPL": 2},
                "currency": "INR",
            }
        )

        self.assertEqual(result["stock_prices"]["AAPL"], 832.5)
        self.assertEqual(result["portfolio_value"], 1665.0)
        self.assertEqual(result["portfolio_details"]["currency"], "INR")
        self.assertEqual(
            result["portfolio_details"]["holdings"][0]["current_price"],
            832.5,
        )


if __name__ == "__main__":
    unittest.main()
