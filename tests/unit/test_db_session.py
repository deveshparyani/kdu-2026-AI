import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.session import (
    build_database_engine_options,
    create_database_session_manager,
)

pytestmark = pytest.mark.anyio


async def test_session_manager_builds_async_engine_and_sessions() -> None:
    settings = Settings(
        DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/test_db",
    )
    session_manager = create_database_session_manager(settings)

    session = session_manager.session_factory()
    try:
        assert session_manager.engine.url.drivername == "postgresql+psycopg"
        assert isinstance(session, AsyncSession)
    finally:
        await session.close()
        await session_manager.dispose()


async def test_session_manager_yields_distinct_request_scoped_sessions() -> None:
    settings = Settings(
        DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/test_db",
    )
    session_manager = create_database_session_manager(settings)

    first_session_generator = session_manager.get_session()
    second_session_generator = session_manager.get_session()

    try:
        first_session = await first_session_generator.__anext__()
        second_session = await second_session_generator.__anext__()

        assert first_session is not second_session
    finally:
        await first_session_generator.aclose()
        await second_session_generator.aclose()
        await session_manager.dispose()


def test_sqlite_engine_options_skip_postgres_pool_configuration() -> None:
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///./template-test.db",
    )

    assert build_database_engine_options(settings) == {
        "echo": False,
    }
