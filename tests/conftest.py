from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AppEnv, AuthIdentifierMode, Settings, get_settings
from app.core.security import SecurityManager
from app.db.base import Base
from app.db.session import (
    DatabaseSessionManager,
    create_database_session_manager,
    get_db_session,
)
from app.main import create_app
from app.models.user import User, UserRole
from app.repositories.user import SQLAlchemyUserRepository

CreateUserFixture = Callable[..., Awaitable[User]]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def build_test_settings(
    *,
    database_url: str,
    auth_identifier_mode: AuthIdentifierMode = AuthIdentifierMode.EMAIL,
    **overrides: object,
) -> Settings:
    settings_values: dict[str, object] = {
        "APP_ENV": AppEnv.TEST,
        "APP_DEBUG": False,
        "AUTH_ENABLED": True,
        "AUTH_IDENTIFIER_MODE": auth_identifier_mode,
        "AUTH_JWT_SECRET": "super-secret-test-key-with-32-chars",
        "AUTH_JWT_ISSUER": "test-suite",
        "AUTH_JWT_AUDIENCE": "test-clients",
        "AUTH_PASSWORD_MIN_LENGTH": 8,
        "CORS_ALLOW_ORIGINS": "http://localhost:3000",
        "DATABASE_URL": database_url,
        "TEST_DATABASE_URL": database_url,
        "DATABASE_ECHO": False,
    }
    settings_values.update(overrides)
    return Settings(**cast(Any, settings_values))


@pytest.fixture
def test_database_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def auth_settings(test_database_url: str) -> Settings:
    return build_test_settings(database_url=test_database_url)


@pytest.fixture
async def db_session_manager(
    auth_settings: Settings,
) -> AsyncIterator[DatabaseSessionManager]:
    session_manager = create_database_session_manager(auth_settings)
    async with session_manager.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    try:
        yield session_manager
    finally:
        async with session_manager.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await session_manager.dispose()


@pytest.fixture
async def db_session(
    db_session_manager: DatabaseSessionManager,
) -> AsyncIterator[AsyncSession]:
    async with db_session_manager.session_factory() as session:
        yield session


@pytest.fixture
def user_repository(db_session: AsyncSession) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(session=db_session)


@pytest.fixture
def create_user(
    auth_settings: Settings,
    db_session_manager: DatabaseSessionManager,
) -> CreateUserFixture:
    security = SecurityManager(auth_settings)

    async def _create_user(
        *,
        email: str | None = None,
        username: str | None = None,
        password: str = "StrongPass123!",
        role: UserRole = UserRole.USER,
        is_active: bool = True,
        is_verified: bool = False,
    ) -> User:
        async with db_session_manager.session_factory() as session:
            repository = SQLAlchemyUserRepository(session=session)
            return await repository.create(
                email=email,
                username=username,
                password_hash=security.hash_password(password),
                role=role,
                is_active=is_active,
                is_verified=is_verified,
            )

    return _create_user


@pytest.fixture
def auth_app(
    auth_settings: Settings,
    db_session_manager: DatabaseSessionManager,
) -> FastAPI:
    app = create_app(auth_settings)

    async def override_db_session() -> AsyncIterator[AsyncSession]:
        async for session in db_session_manager.get_session():
            yield session

    def override_settings() -> Settings:
        return auth_settings

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_settings] = override_settings
    return app


@pytest.fixture
async def auth_client(auth_app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=auth_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as async_client:
        yield async_client


@pytest.fixture
async def client(auth_app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=auth_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as async_client:
        yield async_client
