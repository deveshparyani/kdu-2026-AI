from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.repositories.user import SQLAlchemyUserRepository
from app.services.auth import AuthService
from app.services.health import HealthService, ReadinessService

SettingsDependency = Annotated[Settings, Depends(get_settings)]
DBSessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


async def get_health_service(
    settings: SettingsDependency,
) -> AsyncIterator[HealthService]:
    yield HealthService(settings=settings)


async def get_readiness_service(
    settings: SettingsDependency,
    session: DBSessionDependency,
) -> AsyncIterator[ReadinessService]:
    yield ReadinessService(settings=settings, session=session)


async def get_user_repository(
    session: DBSessionDependency,
) -> AsyncIterator[SQLAlchemyUserRepository]:
    yield SQLAlchemyUserRepository(session=session)


async def get_auth_service(
    settings: SettingsDependency,
) -> AsyncIterator[AuthService]:
    yield AuthService(settings=settings)


HealthServiceDependency = Annotated[HealthService, Depends(get_health_service)]
ReadinessServiceDependency = Annotated[
    ReadinessService,
    Depends(get_readiness_service),
]
UserRepositoryDependency = Annotated[
    SQLAlchemyUserRepository,
    Depends(get_user_repository),
]
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
