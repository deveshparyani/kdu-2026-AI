from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AuthIdentifierMode, Settings, get_settings
from app.core.security import SecurityManager
from app.db.base import Base
from app.db.session import DatabaseSessionManager, get_db_session
from app.main import create_app
from app.repositories.user import SQLAlchemyUserRepository
from tests.conftest import build_test_settings

pytestmark = pytest.mark.anyio


@asynccontextmanager
async def build_custom_auth_client(
    test_database_url: str,
    **setting_overrides: object,
) -> AsyncIterator[tuple[AsyncClient, DatabaseSessionManager, Settings]]:
    settings = build_test_settings(
        database_url=test_database_url,
        **cast(Any, setting_overrides),
    )
    session_manager = DatabaseSessionManager(settings)

    async with session_manager.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    app = create_app(settings)

    async def override_db_session() -> AsyncIterator[AsyncSession]:
        async for session in session_manager.get_session():
            yield session

    def override_settings() -> Settings:
        return settings

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_settings] = override_settings

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            yield client, session_manager, settings
    finally:
        async with session_manager.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await session_manager.dispose()


async def test_successful_registration(
    auth_client: AsyncClient,
    auth_settings: Settings,
    db_session_manager: DatabaseSessionManager,
) -> None:
    response = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "StrongPass123!",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"
    assert "password_hash" not in response.json()

    async with db_session_manager.session_factory() as session:
        repository = SQLAlchemyUserRepository(session=session)
        persisted_user = await repository.get_by_email("user@example.com")

    assert persisted_user is not None
    assert persisted_user.password_hash != "StrongPass123!"
    assert SecurityManager(auth_settings).verify_password(
        "StrongPass123!",
        persisted_user.password_hash,
    )


async def test_duplicate_registration(auth_client: AsyncClient) -> None:
    payload = {
        "email": "duplicate@example.com",
        "password": "StrongPass123!",
    }
    await auth_client.post("/api/v1/auth/register", json=payload)

    response = await auth_client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 409
    assert response.json() == {
        "detail": {
            "code": "duplicate_user",
            "message": "A user with that email already exists.",
            "fields": [],
        }
    }


async def test_invalid_email(auth_client: AsyncClient) -> None:
    response = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "StrongPass123!",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "validation_error"


async def test_weak_password(auth_client: AsyncClient) -> None:
    response = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "weak@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": {
            "code": "validation_error",
            "message": "Invalid registration data.",
            "fields": [
                {
                    "field": "password",
                    "message": (
                        "Value error, Password must be at least 8 characters long."
                    ),
                }
            ],
        }
    }


async def test_successful_login(auth_client: AsyncClient) -> None:
    await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "StrongPass123!",
        },
    )

    response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "login@example.com",
            "password": "StrongPass123!",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login@example.com"
    assert data["access_token"]
    assert data["refresh_token"]


async def test_invalid_credentials(auth_client: AsyncClient) -> None:
    await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpass@example.com",
            "password": "StrongPass123!",
        },
    )

    response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "wrongpass@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": {
            "code": "invalid_credentials",
            "message": "Invalid credentials.",
            "fields": [],
        }
    }


async def test_duplicate_username_registration_in_either_mode(
    test_database_url: str,
) -> None:
    async with build_custom_auth_client(
        test_database_url,
        auth_identifier_mode=AuthIdentifierMode.EITHER,
    ) as (client, _, _):
        first_response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "shared_name",
                "password": "StrongPass123!",
            },
        )
        second_response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "shared_name",
                "password": "StrongPass123!",
            },
        )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"]["code"] == "duplicate_user"


async def test_refresh_returns_rotated_tokens(auth_client: AsyncClient) -> None:
    await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@example.com",
            "password": "StrongPass123!",
        },
    )
    login_response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "refresh@example.com",
            "password": "StrongPass123!",
        },
    )

    refresh_response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_response.json()["refresh_token"]},
    )

    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"] != login_response.json()[
        "access_token"
    ]
    assert refresh_response.json()["refresh_token"] != login_response.json()[
        "refresh_token"
    ]


async def test_logout_returns_message(auth_client: AsyncClient) -> None:
    await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout@example.com",
            "password": "StrongPass123!",
        },
    )
    login_response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "logout@example.com",
            "password": "StrongPass123!",
        },
    )
    access_token = login_response.json()["access_token"]

    response = await auth_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Logout completed. Discard existing client tokens."
    }


async def test_password_reset_flow_updates_password(auth_client: AsyncClient) -> None:
    await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "reset@example.com",
            "password": "StrongPass123!",
        },
    )

    request_response = await auth_client.post(
        "/api/v1/auth/password-reset/request",
        json={"identifier": "reset@example.com"},
    )
    reset_token = request_response.json()["token"]

    confirm_response = await auth_client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "token": reset_token,
            "new_password": "NewStrongPass123!",
        },
    )
    old_login_response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "reset@example.com",
            "password": "StrongPass123!",
        },
    )
    new_login_response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "reset@example.com",
            "password": "NewStrongPass123!",
        },
    )

    assert request_response.status_code == 202
    assert request_response.json()["token"]
    assert confirm_response.status_code == 200
    assert old_login_response.status_code == 401
    assert new_login_response.status_code == 200


async def test_registration_disabled_returns_403(test_database_url: str) -> None:
    async with build_custom_auth_client(
        test_database_url,
        AUTH_ALLOW_SELF_SIGNUP=False,
    ) as (client, _, _):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "blocked@example.com",
                "password": "StrongPass123!",
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "registration_disabled"


async def test_email_verification_flow_unblocks_login(test_database_url: str) -> None:
    async with build_custom_auth_client(
        test_database_url,
        AUTH_REQUIRE_EMAIL_VERIFICATION=True,
    ) as (client, _, _):
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "verify@example.com",
                "password": "StrongPass123!",
            },
        )
        blocked_login = await client.post(
            "/api/v1/auth/login",
            json={
                "identifier": "verify@example.com",
                "password": "StrongPass123!",
            },
        )
        request_response = await client.post(
            "/api/v1/auth/email-verification/request",
            json={"identifier": "verify@example.com"},
        )
        token = request_response.json()["token"]
        confirm_response = await client.post(
            "/api/v1/auth/email-verification/confirm",
            json={"token": token},
        )
        successful_login = await client.post(
            "/api/v1/auth/login",
            json={
                "identifier": "verify@example.com",
                "password": "StrongPass123!",
            },
        )

    assert register_response.status_code == 201
    assert blocked_login.status_code == 403
    assert blocked_login.json()["detail"]["code"] == "email_verification_required"
    assert request_response.status_code == 202
    assert token
    assert confirm_response.status_code == 200
    assert confirm_response.json()["is_verified"] is True
    assert successful_login.status_code == 200
