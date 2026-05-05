import asyncio
import tempfile
import unittest
from pathlib import Path

from customer_service.concurrency import AsyncServiceGate, ServiceOverloadedError
from customer_service.logging_utils import StructuredLogger


class PhaseThreeConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_gate_rejects_when_queue_is_full(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = StructuredLogger(Path(temp_dir), verbose=False)
            gate = AsyncServiceGate("db", max_concurrent=1, max_queue_size=0, logger=logger)

            with self.assertRaises(ServiceOverloadedError):
                await gate.run("trace-1", {"query": "hello"}, lambda: asyncio.sleep(0.01))

    async def test_gate_runs_operation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = StructuredLogger(Path(temp_dir), verbose=False)
            gate = AsyncServiceGate("db", max_concurrent=1, max_queue_size=2, logger=logger)

            async def op():
                await asyncio.sleep(0.01)
                return "ok"

            result = await gate.run("trace-2", {"query": "hello"}, op)
            self.assertEqual(result, "ok")


if __name__ == "__main__":
    unittest.main()
