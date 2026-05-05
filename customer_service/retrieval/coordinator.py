from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from time import perf_counter
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from ..concurrency import AsyncServiceGate, ServiceOverloadedError
from ..config import Settings
from ..logging_utils import StructuredLogger
from .repositories import UpstreamServiceError
from .schemas import ConsensusOutput, CoordinatorResult, WorkerSearchResult
from .security import QuerySecurityGuard, SecurityValidationError

if TYPE_CHECKING:
    from .crews import RetrievalCrewFactory


WorkerRunner = Callable[[str, str], Awaitable[WorkerSearchResult]]


class RetrievalCoordinator:
    def __init__(
        self,
        settings: Settings,
        logger: StructuredLogger,
        crew_factory: Optional["RetrievalCrewFactory"] = None,
        db_runner: Optional[WorkerRunner] = None,
        vector_runner: Optional[WorkerRunner] = None,
    ) -> None:
        self._settings = settings
        self._logger = logger
        if crew_factory is None:
            from .crews import RetrievalCrewFactory

            crew_factory = RetrievalCrewFactory(settings)
        self._crew_factory = crew_factory
        self._db_runner = db_runner or self._crew_factory.run_db_worker
        self._vector_runner = vector_runner or self._crew_factory.run_vector_worker
        self._db_gate = AsyncServiceGate(
            service_name="database",
            max_concurrent=settings.db_max_concurrency,
            max_queue_size=settings.db_max_queue_size,
            logger=logger,
        )
        self._vector_gate = AsyncServiceGate(
            service_name="vector",
            max_concurrent=settings.vector_max_concurrency,
            max_queue_size=settings.vector_max_queue_size,
            logger=logger,
        )
        self._consensus_gate = AsyncServiceGate(
            service_name="consensus",
            max_concurrent=settings.consensus_max_concurrency,
            max_queue_size=settings.consensus_max_queue_size,
            logger=logger,
        )

    async def handle_query(self, query: str) -> CoordinatorResult:
        safe_query = QuerySecurityGuard.validate_user_query(query)
        trace_id = str(uuid4())
        self._logger.emit("retrieval_coordinator_started", trace_id=trace_id, query=safe_query)

        db_task = asyncio.create_task(self._execute_worker("db_agent", "database", self._db_runner, safe_query, trace_id))
        vector_task = asyncio.create_task(
            self._execute_worker("vector_agent", "vector", self._vector_runner, safe_query, trace_id)
        )
        db_result, vector_result = await asyncio.gather(db_task, vector_task)

        executed_in_parallel = _intervals_overlap(
            db_result.started_at,
            db_result.finished_at,
            vector_result.started_at,
            vector_result.finished_at,
        )

        warnings: list[str] = []
        if db_result.status == "failed":
            warnings.append(f"DB worker failed: {db_result.error}")
        if vector_result.status == "failed":
            warnings.append(f"Vector worker failed: {vector_result.error}")

        if db_result.status == "failed" and vector_result.status == "failed":
            consensus = ConsensusOutput(
                final_answer="I could not retrieve trusted information from either data source right now.",
                decision_basis="Both worker agents failed, so the coordinator returned a safe fallback instead of inventing an answer.",
                confidence=0.0,
                sources_used=[],
                degraded=True,
                can_answer=False,
            )
        elif (
            self._settings.retrieval_skip_consensus_on_single_success
            and (db_result.status == "failed" or vector_result.status == "failed")
        ):
            consensus = self._build_degraded_consensus(db_result, vector_result)
            warnings.append("Consensus agent skipped to reduce cost because only one worker succeeded.")
        elif self._consensus_gate.is_under_pressure():
            consensus = self._build_degraded_consensus(db_result, vector_result)
            warnings.append("Consensus agent skipped because the consensus queue is under pressure.")
        else:
            self._logger.emit(
                "consensus_payload_prepared",
                trace_id=trace_id,
                payload={
                    "db_result": db_result.compact_for_prompt(
                        max_records=self._settings.retrieval_prompt_records,
                        max_snippet_chars=self._settings.retrieval_prompt_snippet_chars,
                    ),
                    "vector_result": vector_result.compact_for_prompt(
                        max_records=self._settings.retrieval_prompt_records,
                        max_snippet_chars=self._settings.retrieval_prompt_snippet_chars,
                    ),
                },
            )
            consensus = await self._consensus_gate.run(
                trace_id=trace_id,
                payload={"query": safe_query},
                operation=lambda: self._crew_factory.run_consensus(safe_query, db_result, vector_result, trace_id),
            )

        result = CoordinatorResult(
            trace_id=trace_id,
            query=safe_query,
            executed_in_parallel=executed_in_parallel,
            db_result=db_result,
            vector_result=vector_result,
            consensus=consensus,
            warnings=warnings,
        )
        self._logger.emit(
            "retrieval_coordinator_completed",
            trace_id=trace_id,
            executed_in_parallel=executed_in_parallel,
            warnings=warnings,
            consensus=consensus.model_dump(mode="json"),
        )
        return result

    async def _execute_worker(
        self,
        worker_name: str,
        source_type: str,
        runner: WorkerRunner,
        query: str,
        trace_id: str,
    ) -> WorkerSearchResult:
        started_at = datetime.now(timezone.utc)
        started_perf = perf_counter()
        self._logger.emit("worker_dispatch_started", trace_id=trace_id, worker_name=worker_name)
        try:
            gate = self._db_gate if source_type == "database" else self._vector_gate
            result = await gate.run(
                trace_id=trace_id,
                payload={"worker_name": worker_name, "query": query},
                operation=lambda: asyncio.wait_for(
                    runner(query, trace_id),
                    timeout=self._settings.retrieval_worker_timeout_seconds,
                ),
            )
            finished_at = datetime.now(timezone.utc)
            latency_ms = int((perf_counter() - started_perf) * 1000)
            normalized = result.model_copy(
                update={
                    "trace_id": trace_id,
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "latency_ms": latency_ms,
                }
            )
            self._logger.emit(
                "worker_dispatch_completed",
                trace_id=trace_id,
                worker_name=worker_name,
                latency_ms=latency_ms,
                status=normalized.status,
                payload=normalized.model_dump(mode="json"),
            )
            return normalized
        except (
            SecurityValidationError,
            ServiceOverloadedError,
            UpstreamServiceError,
            TimeoutError,
            asyncio.TimeoutError,
            Exception,
        ) as exc:
            finished_at = datetime.now(timezone.utc)
            latency_ms = int((perf_counter() - started_perf) * 1000)
            blocked_for_security = isinstance(exc, SecurityValidationError)
            failure = WorkerSearchResult(
                worker_name=worker_name,  # type: ignore[arg-type]
                source_type=source_type,  # type: ignore[arg-type]
                status="failed",
                confidence=0.0,
                summary=f"{worker_name} failed to retrieve data.",
                error=str(exc),
                trace_id=trace_id,
                started_at=started_at,
                finished_at=finished_at,
                latency_ms=latency_ms,
                blocked_for_security=blocked_for_security,
            )
            self._logger.emit(
                "worker_dispatch_failed",
                trace_id=trace_id,
                worker_name=worker_name,
                latency_ms=latency_ms,
                blocked_for_security=blocked_for_security,
                error=str(exc),
                payload=failure.model_dump(mode="json"),
            )
            return failure

    def _build_degraded_consensus(
        self,
        db_result: WorkerSearchResult,
        vector_result: WorkerSearchResult,
    ) -> ConsensusOutput:
        if db_result.status == "success":
            top = db_result.records[0] if db_result.records else None
            message = top.snippet if top else db_result.summary
            return ConsensusOutput(
                final_answer=message,
                decision_basis="Returned database evidence directly in degraded mode to save latency and token cost.",
                confidence=db_result.confidence,
                sources_used=["database"],
                degraded=True,
                can_answer=True,
            )
        if vector_result.status == "success":
            top = vector_result.records[0] if vector_result.records else None
            message = top.snippet if top else vector_result.summary
            return ConsensusOutput(
                final_answer=message,
                decision_basis="Returned vector evidence directly in degraded mode to save latency and token cost.",
                confidence=vector_result.confidence * 0.9,
                sources_used=["vector"],
                degraded=True,
                can_answer=True,
            )
        return ConsensusOutput(
            final_answer="I could not retrieve trusted information right now.",
            decision_basis="No successful worker output was available for degraded mode.",
            confidence=0.0,
            sources_used=[],
            degraded=True,
            can_answer=False,
        )


def _intervals_overlap(
    start_a: datetime,
    end_a: datetime,
    start_b: datetime,
    end_b: datetime,
) -> bool:
    return max(start_a, start_b) < min(end_a, end_b)
