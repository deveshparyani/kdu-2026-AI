from __future__ import annotations

import asyncio
import json
import sys

from .config import Settings
from .event_listener import CrewMonitoringListener
from .logging_utils import StructuredLogger
from .retrieval.coordinator import RetrievalCoordinator


async def _run(query: str) -> None:
    settings = Settings.load()
    logger = StructuredLogger(settings.log_dir, verbose=settings.verbose)
    _listener = CrewMonitoringListener(logger)
    coordinator = RetrievalCoordinator(settings, logger)
    result = await coordinator.handle_query(query)
    print(json.dumps(result.model_dump(mode="json"), indent=2))


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit('Usage: customer-service query "Why was I charged twice this month?"')
    asyncio.run(_run(sys.argv[1]))


if __name__ == "__main__":
    main()
