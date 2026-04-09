from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.protected import router as protected_router
from app.core.config import Settings


def build_api_router(settings: Settings) -> APIRouter:
    api_router = APIRouter(prefix=settings.api_v1_prefix)

    if settings.auth_enabled:
        api_router.include_router(auth_router)
        api_router.include_router(protected_router)

    if settings.feature_healthcheck_enabled:
        api_router.include_router(health_router)

    return api_router
