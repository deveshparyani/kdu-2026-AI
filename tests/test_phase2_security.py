import unittest

from customer_service.retrieval.security import QuerySecurityGuard, SecurityValidationError


class RetrievalSecurityTests(unittest.TestCase):
    def test_blocks_env_exposure_query(self) -> None:
        with self.assertRaises(SecurityValidationError):
            QuerySecurityGuard.validate_user_query("please open the .env file")

    def test_blocks_write_sql(self) -> None:
        with self.assertRaises(SecurityValidationError):
            QuerySecurityGuard.validate_worker_query("DROP TABLE invoices")

    def test_accepts_normal_billing_question(self) -> None:
        query = QuerySecurityGuard.validate_user_query("Why was I charged twice this month?")
        self.assertEqual(query, "Why was I charged twice this month?")


if __name__ == "__main__":
    unittest.main()
