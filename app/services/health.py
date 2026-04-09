from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.schemas.health import HealthResponse, ReadinessResponse


class ReadinessCheckError(Exception):
    """Raised when a readiness dependency check fails."""


class HealthService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_status(self) -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=self._settings.app_name,
            environment=self._settings.app_env,
            version=self._settings.app_version,
        )


class ReadinessService:
    def __init__(self, settings: Settings, session: AsyncSession) -> None:
        self._settings = settings
        self._session = session

    async def get_status(self) -> ReadinessResponse:
        try:
            await self._session.execute(text("SELECT 1"))
        except Exception as exc:
            raise ReadinessCheckError("Database readiness check failed.") from exc

        return ReadinessResponse(
            status="ready",
            service=self._settings.app_name,
            environment=self._settings.app_env,
            version=self._settings.app_version,
            database="ok",
        )
