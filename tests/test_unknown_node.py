import unittest
from types import SimpleNamespace

from app.graph.workflow import route_after_parse
from app.nodes.unknown import unknown
import app.nodes.unknown as unknown_module


class UnknownNodeTests(unittest.TestCase):
    def setUp(self):
        self.original_model = unknown_module.model

    def tearDown(self):
        unknown_module.model = self.original_model

    def test_route_after_parse_handles_unknown(self):
        self.assertEqual(route_after_parse({"intent": "unknown"}), "unknown")

    def test_unknown_node_returns_model_response(self):
        unknown_module.model = SimpleNamespace(
            invoke=lambda messages: SimpleNamespace(
                content="You can look at large, stable companies and diversify."
            )
        )

        result = unknown({"user_query": "which stock should you suggest?"})

        self.assertEqual(
            result["assistant_response"],
            "You can look at large, stable companies and diversify.",
        )

    def test_unknown_node_handles_missing_query(self):
        result = unknown({})
        self.assertIn("could not find a user message", result["assistant_response"].lower())

    def test_unknown_node_handles_model_failure(self):
        def raise_error(messages):
            raise ValueError("model error")

        unknown_module.model = SimpleNamespace(invoke=raise_error)

        result = unknown({"user_query": "hello"})

        self.assertIn("I can help with stock prices", result["assistant_response"])


if __name__ == "__main__":
    unittest.main()
