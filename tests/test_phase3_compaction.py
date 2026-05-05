import unittest

from customer_service.state import SessionState


class PhaseThreeCompactionTests(unittest.TestCase):
    def test_compacted_view_limits_recent_turns_and_estimates_tokens(self) -> None:
        state = SessionState()
        for index in range(8):
            state.add_user_turn(f"user message {index} " * 10)
            state.add_assistant_turn(f"assistant message {index} " * 10)

        compacted = state.compacted_view(
            max_recent_turns=4,
            max_message_chars=60,
            max_summary_chars=120,
        )

        self.assertLessEqual(len(compacted.recent_messages), 4)
        self.assertLessEqual(len(compacted.conversation_summary), 120)
        self.assertGreater(compacted.estimated_tokens, 0)
        self.assertTrue(compacted.compacted)


if __name__ == "__main__":
    unittest.main()
