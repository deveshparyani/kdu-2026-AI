from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status

from app.api.dependencies.common import (
    HealthServiceDependency,
    ReadinessServiceDependency,
)
from app.core.exceptions import create_http_error
from app.schemas.errors import ErrorResponse
from app.schemas.health import HealthResponse, ReadinessResponse
from app.services.health import ReadinessCheckError

router = APIRouter(prefix="/health", tags=["health"])

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    503: {"model": ErrorResponse},
}


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
)
async def get_health(service: HealthServiceDependency) -> HealthResponse:
    return await service.get_status()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    responses=ERROR_RESPONSES,
)
async def get_readiness(
    service: ReadinessServiceDependency,
) -> ReadinessResponse:
    try:
        return await service.get_status()
    except ReadinessCheckError as exc:
        raise create_http_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            code="service_unavailable",
            message=str(exc),
        ) from exc
