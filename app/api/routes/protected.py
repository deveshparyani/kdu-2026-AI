from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status

from app.api.dependencies.auth import AdminUserDependency, AuthenticatedUserDependency
from app.schemas.auth import AccessContextResponse
from app.schemas.errors import ErrorResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
}


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the current authenticated user",
    responses=ERROR_RESPONSES,
)
async def get_authenticated_user_profile(
    current_user: AuthenticatedUserDependency,
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.get(
    "/admin",
    response_model=AccessContextResponse,
    status_code=status.HTTP_200_OK,
    summary="Check admin-only access",
    responses=ERROR_RESPONSES,
)
async def get_admin_access_context(
    current_user: AdminUserDependency,
) -> AccessContextResponse:
    return AccessContextResponse(
        message="Admin access granted.",
        user=UserResponse.model_validate(current_user),
    )
