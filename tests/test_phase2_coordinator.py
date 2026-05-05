import asyncio
import unittest
from datetime import datetime, timezone

from customer_service.retrieval.coordinator import RetrievalCoordinator
from customer_service.retrieval.schemas import SearchRecord, WorkerSearchResult


class FakeSettings:
    retrieval_worker_timeout_seconds = 2.0
    verbose = False
    agent_model = "test-model"
    retrieval_max_results = 3
    db_max_concurrency = 4
    db_max_queue_size = 10
    vector_max_concurrency = 4
    vector_max_queue_size = 10
    consensus_max_concurrency = 2
    consensus_max_queue_size = 5
    retrieval_skip_consensus_on_single_success = True
    retrieval_prompt_records = 2
    retrieval_prompt_snippet_chars = 120


class FakeLogger:
    def emit(self, event: str, **payload) -> None:
        return None


def _success_result(worker_name: str, source_type: str, trace_id: str) -> WorkerSearchResult:
    return WorkerSearchResult(
        worker_name=worker_name,  # type: ignore[arg-type]
        source_type=source_type,  # type: ignore[arg-type]
        status="success",
        confidence=0.8,
        summary=f"{worker_name} succeeded",
        records=[
            SearchRecord(
                record_id=f"{worker_name}-1",
                title="record",
                snippet="snippet",
                source=source_type,
                score=0.9,
            )
        ],
        trace_id=trace_id,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        latency_ms=0,
    )


class FakeCrewFactory:
    async def run_db_worker(self, query: str, trace_id: str) -> WorkerSearchResult:
        await asyncio.sleep(0.05)
        return _success_result("db_agent", "database", trace_id)

    async def run_vector_worker(self, query: str, trace_id: str) -> WorkerSearchResult:
        await asyncio.sleep(0.05)
        return _success_result("vector_agent", "vector", trace_id)

    async def run_consensus(self, query, db_result, vector_result, trace_id):
        from customer_service.retrieval.schemas import ConsensusOutput

        return ConsensusOutput(
            final_answer="Combined answer",
            decision_basis="Both sources contributed.",
            confidence=0.9,
            sources_used=["database", "vector"],
            degraded=False,
            can_answer=True,
        )


class RetrievalCoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_parallel_success_path(self) -> None:
        coordinator = RetrievalCoordinator(FakeSettings(), FakeLogger(), crew_factory=FakeCrewFactory())
        result = await coordinator.handle_query("Why was I charged twice?")
        self.assertTrue(result.executed_in_parallel)
        self.assertEqual(result.db_result.status, "success")
        self.assertEqual(result.vector_result.status, "success")
        self.assertEqual(result.consensus.final_answer, "Combined answer")

    async def test_partial_failure_still_returns_answer(self) -> None:
        class PartialFailureFactory(FakeCrewFactory):
            async def run_vector_worker(self, query: str, trace_id: str) -> WorkerSearchResult:
                raise RuntimeError("HTTP 500")

            async def run_consensus(self, query, db_result, vector_result, trace_id):
                from customer_service.retrieval.schemas import ConsensusOutput

                return ConsensusOutput(
                    final_answer="Using only DB evidence.",
                    decision_basis="Vector failed, DB succeeded.",
                    confidence=0.6,
                    sources_used=["database"],
                    degraded=True,
                    can_answer=True,
                )

        coordinator = RetrievalCoordinator(FakeSettings(), FakeLogger(), crew_factory=PartialFailureFactory())
        result = await coordinator.handle_query("Why was I charged twice?")
        self.assertEqual(result.db_result.status, "success")
        self.assertEqual(result.vector_result.status, "failed")
        self.assertTrue(result.consensus.degraded)

    async def test_both_fail_returns_safe_fallback(self) -> None:
        class FailureFactory(FakeCrewFactory):
            async def run_db_worker(self, query: str, trace_id: str) -> WorkerSearchResult:
                raise RuntimeError("DB down")

            async def run_vector_worker(self, query: str, trace_id: str) -> WorkerSearchResult:
                raise RuntimeError("Vector down")

        coordinator = RetrievalCoordinator(FakeSettings(), FakeLogger(), crew_factory=FailureFactory())
        result = await coordinator.handle_query("Why was I charged twice?")
        self.assertFalse(result.consensus.can_answer)
        self.assertEqual(result.db_result.status, "failed")
        self.assertEqual(result.vector_result.status, "failed")


if __name__ == "__main__":
    unittest.main()
