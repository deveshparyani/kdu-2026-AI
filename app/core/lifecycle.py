import logging
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Callable

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool

from app.core.config import Settings
from app.core.logging import configure_logging
from app.db.migrations import upgrade_database_head


def create_lifespan(
    settings: Settings,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings)
        logger = logging.getLogger("app.lifecycle")
        if settings.run_migrations_on_startup:
            logger.info("database_migration_startup_begin")
            await run_in_threadpool(upgrade_database_head, settings.database_url)
            logger.info("database_migration_startup_complete")
        logger.info(
            "application_startup",
            extra={
                "app_name": settings.app_name,
                "environment": settings.app_env,
                "version": settings.app_version,
            },
        )
        yield
        logger.info("application_shutdown", extra={"app_name": settings.app_name})

    return lifespan
