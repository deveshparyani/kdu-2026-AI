from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.dependencies.common import AuthServiceDependency, UserRepositoryDependency
from app.core.exceptions import create_http_error
from app.core.security import ExpiredTokenError, InvalidTokenError
from app.models.user import User, UserRole
from app.services.auth import CurrentUserNotFoundError, InactiveUserError

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials],
        Depends(bearer_scheme),
    ],
    service: AuthServiceDependency,
    repository: UserRepositoryDependency,
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _not_authenticated_error(
            "Authentication credentials were not provided."
        )

    try:
        return await service.resolve_current_user(
            credentials.credentials,
            repository,
            require_active=True,
        )
    except ExpiredTokenError as exc:
        raise _not_authenticated_error("Authentication token has expired.") from exc
    except (
        InvalidTokenError,
        CurrentUserNotFoundError,
        InactiveUserError,
    ) as exc:
        raise _not_authenticated_error(
            "Authentication credentials are invalid."
        ) from exc


async def require_authenticated_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return current_user


def require_role(*roles: UserRole) -> Callable[[User], Awaitable[User]]:
    async def role_dependency(
        current_user: Annotated[User, Depends(require_authenticated_user)],
    ) -> User:
        if current_user.role not in roles:
            raise create_http_error(
                status.HTTP_403_FORBIDDEN,
                code="forbidden",
                message="You do not have permission to access this resource.",
            )
        return current_user

    return role_dependency


CurrentUserDependency = Annotated[User, Depends(get_current_user)]
AuthenticatedUserDependency = Annotated[User, Depends(require_authenticated_user)]
AdminUserDependency = Annotated[User, Depends(require_role(UserRole.ADMIN))]


def _not_authenticated_error(message: str) -> HTTPException:
    error = create_http_error(
        status.HTTP_401_UNAUTHORIZED,
        code="not_authenticated",
        message=message,
    )
    error.headers = {"WWW-Authenticate": "Bearer"}
    return error
