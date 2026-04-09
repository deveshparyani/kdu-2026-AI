import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_health_endpoint_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "fastapi-template",
        "environment": "test",
        "version": "0.1.0",
    }


async def test_readiness_endpoint_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "fastapi-template",
        "environment": "test",
        "version": "0.1.0",
        "database": "ok",
    }
