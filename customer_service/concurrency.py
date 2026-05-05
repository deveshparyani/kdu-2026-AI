from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Generic, TypeVar

from .logging_utils import StructuredLogger


T = TypeVar("T")


class ServiceOverloadedError(RuntimeError):
    """Raised when a protected external system queue is full."""


@dataclass
class GateStats:
    service_name: str
    max_concurrent: int
    max_queue_size: int
    in_flight: int = 0
    queued: int = 0

    @property
    def pressure_ratio(self) -> float:
        if self.max_queue_size <= 0:
            return 0.0
        return min(1.0, self.queued / self.max_queue_size)


class AsyncServiceGate(Generic[T]):
    def __init__(
        self,
        service_name: str,
        max_concurrent: int,
        max_queue_size: int,
        logger: StructuredLogger,
    ) -> None:
        self._stats = GateStats(
            service_name=service_name,
            max_concurrent=max_concurrent,
            max_queue_size=max_queue_size,
        )
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._lock = asyncio.Lock()
        self._logger = logger

    @property
    def stats(self) -> GateStats:
        return self._stats

    def is_under_pressure(self) -> bool:
        return self._stats.pressure_ratio >= 0.6 or self._stats.in_flight >= self._stats.max_concurrent

    async def run(
        self,
        trace_id: str,
        payload: dict[str, Any],
        operation: Callable[[], Awaitable[T]],
    ) -> T:
        queue_started = perf_counter()
        async with self._lock:
            if self._stats.queued >= self._stats.max_queue_size:
                self._logger.emit(
                    "service_gate_rejected",
                    trace_id=trace_id,
                    service_name=self._stats.service_name,
                    queued=self._stats.queued,
                    max_queue_size=self._stats.max_queue_size,
                    payload=payload,
                )
                raise ServiceOverloadedError(
                    f"{self._stats.service_name} queue is full. Request rejected to protect the dependency."
                )
            self._stats.queued += 1

        await self._semaphore.acquire()
        wait_ms = int((perf_counter() - queue_started) * 1000)
        async with self._lock:
            self._stats.queued -= 1
            self._stats.in_flight += 1
        self._logger.emit(
            "service_gate_acquired",
            trace_id=trace_id,
            service_name=self._stats.service_name,
            wait_ms=wait_ms,
            in_flight=self._stats.in_flight,
            queued=self._stats.queued,
            payload=payload,
        )
        try:
            return await operation()
        finally:
            async with self._lock:
                self._stats.in_flight -= 1
            self._semaphore.release()
            self._logger.emit(
                "service_gate_released",
                trace_id=trace_id,
                service_name=self._stats.service_name,
                in_flight=self._stats.in_flight,
                queued=self._stats.queued,
            )
