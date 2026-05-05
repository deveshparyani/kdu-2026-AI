import unittest

from customer_service.state import SessionState, truncate_text_by_ratio


class StateTests(unittest.TestCase):
    def test_truncate_text_by_ratio(self) -> None:
        self.assertEqual(truncate_text_by_ratio("hello world", 0.5), "hello")

    def test_session_summary_prunes_old_turns(self) -> None:
        state = SessionState()
        for index in range(12):
            state.add_user_turn(f"user turn {index}")
            state.add_assistant_turn(f"assistant turn {index}")
        self.assertLessEqual(len(state.recent_turns), 8)
        self.assertIn("user turn 0", state.rolling_summary)


if __name__ == "__main__":
    unittest.main()
