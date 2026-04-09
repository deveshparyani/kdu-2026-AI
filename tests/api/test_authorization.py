from __future__ import annotations

from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.core.config import Settings
from app.core.security import SecurityManager
from app.models.user import UserRole
from tests.conftest import CreateUserFixture

pytestmark = pytest.mark.anyio


async def test_protected_route_without_token_returns_401(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json() == {
        "detail": {
            "code": "not_authenticated",
            "message": "Authentication credentials were not provided.",
            "fields": [],
        }
    }


async def test_protected_route_with_invalid_token_returns_401(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": {
            "code": "not_authenticated",
            "message": "Authentication credentials are invalid.",
            "fields": [],
        }
    }


async def test_protected_route_with_expired_token_returns_401(
    auth_client: AsyncClient,
    auth_settings: Settings,
    create_user: CreateUserFixture,
) -> None:
    user = await create_user(
        email="expired@example.com",
        username="expired_user",
        role=UserRole.USER,
    )
    security = SecurityManager(auth_settings)
    token = security.create_access_token(
        user.id,
        expires_delta=timedelta(minutes=-1),
    )

    response = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": {
            "code": "not_authenticated",
            "message": "Authentication token has expired.",
            "fields": [],
        }
    }


async def test_admin_route_with_non_admin_user_returns_403(
    auth_client: AsyncClient,
    auth_settings: Settings,
    create_user: CreateUserFixture,
) -> None:
    user = await create_user(
        email="member@example.com",
        username="member_user",
        role=UserRole.USER,
    )
    token = SecurityManager(auth_settings).create_access_token(user.id)

    response = await auth_client.get(
        "/api/v1/auth/admin",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": {
            "code": "forbidden",
            "message": "You do not have permission to access this resource.",
            "fields": [],
        }
    }


async def test_admin_route_with_admin_user_returns_200(
    auth_client: AsyncClient,
    auth_settings: Settings,
    create_user: CreateUserFixture,
) -> None:
    user = await create_user(
        email="admin@example.com",
        username="admin_user",
        role=UserRole.ADMIN,
    )
    token = SecurityManager(auth_settings).create_access_token(user.id)

    response = await auth_client.get(
        "/api/v1/auth/admin",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Admin access granted.",
        "user": {
            "id": str(user.id),
            "email": "admin@example.com",
            "username": "admin_user",
            "role": "admin",
            "is_active": True,
            "is_verified": False,
        },
    }


async def test_protected_route_rejects_refresh_token(
    auth_client: AsyncClient,
    auth_settings: Settings,
    create_user: CreateUserFixture,
) -> None:
    user = await create_user(
        email="refresh@example.com",
        username="refresh_user",
        role=UserRole.USER,
    )
    token = SecurityManager(auth_settings).create_refresh_token(user.id)

    response = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": {
            "code": "not_authenticated",
            "message": "Authentication credentials are invalid.",
            "fields": [],
        }
    }
