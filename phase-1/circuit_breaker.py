from __future__ import annotations

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    fallback_message: str = (
        "I’m unable to retrieve the active user count right now. Please try again later."
    )
    consecutive_failures: int = 0
    state: str = "closed"

    @property
    def is_open(self) -> bool:
        return self.state == "open"

    def allow_request(self) -> bool:
        return not self.is_open

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.state = "closed"

    def record_failure(self, dependency_name: str) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold and not self.is_open:
            self.state = "open"
            logger.warning(
                "Loop detected: %s failed %s consecutive times. Opening circuit breaker.",
                dependency_name,
                self.consecutive_failures,
            )
