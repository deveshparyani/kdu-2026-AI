from __future__ import annotations

import pytest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient

from app.core.config import AppEnv, Settings
from app.main import create_app

pytestmark = pytest.mark.anyio


async def test_health_endpoint_returns_standard_shape(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "fastapi-template",
        "environment": "test",
        "version": "0.1.0",
    }


async def test_readiness_endpoint_returns_standard_shape(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "fastapi-template",
        "environment": "test",
        "version": "0.1.0",
        "database": "ok",
    }


async def test_validation_error_shape_for_login_request(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.post(
        "/api/v1/auth/login",
        json={"identifier": "user@example.com"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": {
            "code": "validation_error",
            "message": "Invalid request.",
            "fields": [
                {
                    "field": "password",
                    "message": "Field required",
                }
            ],
        }
    }


async def test_internal_error_response_is_sanitized_in_production() -> None:
    settings = Settings(
        APP_ENV=AppEnv.PRODUCTION,
        APP_DEBUG=False,
        SECRET_KEY="production-secret-key",
        AUTH_JWT_SECRET="production-jwt-secret-key",
    )
    app = create_app(settings)
    router = APIRouter()

    @router.get("/boom")
    async def boom() -> dict[str, str]:
        raise RuntimeError("sensitive database details")

    app.include_router(router, prefix=settings.api_v1_prefix)
    transport = ASGITransport(app=app, raise_app_exceptions=False)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/v1/boom")

    assert response.status_code == 500
    assert response.json() == {
        "detail": {
            "code": "internal_server_error",
            "message": "An unexpected error occurred.",
            "fields": [],
        }
    }
