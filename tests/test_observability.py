import unittest
from types import SimpleNamespace

from app.analytics.evaluate_agent import run_local_evaluation
from app.analytics.langsmith_utils import calculate_llm_cost, record_llm_observation
import app.analytics.evaluate_agent as evaluate_agent_module


class ObservabilityTests(unittest.TestCase):
    def setUp(self):
        self.original_evaluation_target = evaluate_agent_module.evaluation_target

    def tearDown(self):
        evaluate_agent_module.evaluation_target = self.original_evaluation_target

    def test_calculate_llm_cost_uses_model_pricing(self):
        usage_metadata = {
            "input_tokens": 1000,
            "output_tokens": 500,
            "total_tokens": 1500,
        }

        costs = calculate_llm_cost("llama-3.1-8b-instant", usage_metadata)

        self.assertEqual(costs["input_cost"], 0.00005)
        self.assertEqual(costs["output_cost"], 0.00004)
        self.assertEqual(costs["total_cost"], 0.00009)

    def test_record_llm_observation_updates_totals(self):
        response = SimpleNamespace(
            usage_metadata={
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
            }
        )

        updated = record_llm_observation(
            {"observability": {}},
            step_name="unknown",
            model_name="llama-3.1-8b-instant",
            response=response,
        )

        self.assertEqual(len(updated["llm_calls"]), 1)
        self.assertEqual(updated["totals"]["input_tokens"], 10)
        self.assertEqual(updated["totals"]["output_tokens"], 5)
        self.assertEqual(updated["totals"]["total_tokens"], 15)
        self.assertGreater(updated["totals"]["estimated_cost_usd"], 0)

    def test_run_local_evaluation_builds_metric_summary(self):
        evaluate_agent_module.evaluation_target = lambda inputs: {
            "response_type": "stock_price",
            "stock": "AAPL",
            "currency": "EUR",
            "message_present": True,
        }

        results = run_local_evaluation(
            [
                {
                    "inputs": {"user_query": "test", "state": {}},
                    "outputs": {
                        "response_type": "stock_price",
                        "stock": "AAPL",
                        "currency": "EUR",
                    },
                }
            ]
        )

        self.assertEqual(results["mode"], "local")
        self.assertEqual(results["example_count"], 1)
        self.assertEqual(results["summary"]["response_type_match"], 1.0)
        self.assertEqual(results["summary"]["currency_match"], 1.0)


if __name__ == "__main__":
    unittest.main()
