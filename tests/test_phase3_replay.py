import tempfile
import unittest
from pathlib import Path

from customer_service.logging_utils import StructuredLogger
from customer_service.replay import ReplayStore


class PhaseThreeReplayTests(unittest.TestCase):
    def test_replay_filters_by_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = StructuredLogger(Path(temp_dir), verbose=False)
            logger.emit("test_event", session_id="s1", trace_id="t1", payload={"value": 1})
            logger.emit("test_event", session_id="s2", trace_id="t2", payload={"value": 2})

            store = ReplayStore(Path(temp_dir))
            events = store.load_events(session_id="s1")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["session_id"], "s1")


if __name__ == "__main__":
    unittest.main()
