from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings


def build_database_engine_options(settings: Settings) -> dict[str, object]:
    url = make_url(settings.database_url)
    options: dict[str, object] = {
        "echo": settings.database_echo,
    }

    if url.get_backend_name() == "sqlite":
        return options

    options.update(
        {
            "pool_pre_ping": settings.database_pool_pre_ping,
            "pool_size": settings.database_pool_size,
            "max_overflow": settings.database_max_overflow,
            "pool_timeout": settings.database_pool_timeout,
            "pool_recycle": settings.database_pool_recycle,
            "connect_args": settings.database_connect_args,
        }
    )
    return options


class DatabaseSessionManager:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine = create_async_engine(
            settings.database_url,
            **build_database_engine_options(settings),
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._session_factory() as session:
            yield session

    async def dispose(self) -> None:
        await self._engine.dispose()


def create_database_session_manager(settings: Settings) -> DatabaseSessionManager:
    return DatabaseSessionManager(settings)


@lru_cache(maxsize=1)
def get_database_session_manager() -> DatabaseSessionManager:
    return create_database_session_manager(get_settings())


def get_database_engine() -> AsyncEngine:
    return get_database_session_manager().engine


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return get_database_session_manager().session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session_manager = get_database_session_manager()
    async for session in session_manager.get_session():
        yield session
