from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status

from app.api.dependencies.auth import AuthenticatedUserDependency
from app.api.dependencies.common import AuthServiceDependency, UserRepositoryDependency
from app.core.exceptions import create_http_error
from app.core.security import ExpiredTokenError, InvalidTokenError
from app.schemas.auth import (
    ActionTokenResponse,
    EmailVerificationConfirmRequest,
    EmailVerificationRequest,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegistrationRequest,
    TokenResponse,
)
from app.schemas.errors import ErrorResponse
from app.schemas.user import UserResponse
from app.services.auth import (
    CurrentUserNotFoundError,
    DuplicateUserError,
    EmailVerificationRequiredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidIdentifierError,
    RegistrationDisabledError,
    ServiceValidationError,
)

router = APIRouter(prefix="/auth", tags=["auth"])

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses=ERROR_RESPONSES,
)
async def register_user(
    payload: RegistrationRequest,
    service: AuthServiceDependency,
    repository: UserRepositoryDependency,
) -> UserResponse:
    try:
        user = await service.register_user(
            repository,
            email=payload.email,
            username=payload.username,
            password=payload.password.get_secret_value(),
        )
    except DuplicateUserError as exc:
        raise create_http_error(
            status.HTTP_409_CONFLICT,
            code="duplicate_user",
            message=str(exc),
        ) from exc
    except RegistrationDisabledError as exc:
        raise create_http_error(
            status.HTTP_403_FORBIDDEN,
            code="registration_disabled",
            message=str(exc),
        ) from exc
    except ServiceValidationError as exc:
        raise create_http_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="validation_error",
            message=exc.message,
            fields=exc.fields,
        ) from exc

    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate a user",
    responses=ERROR_RESPONSES,
)
async def login_user(
    payload: LoginRequest,
    service: AuthServiceDependency,
    repository: UserRepositoryDependency,
) -> TokenResponse:
    try:
        result = await service.authenticate_user(
            repository,
            identifier=payload.identifier,
            password=payload.password.get_secret_value(),
        )
    except InvalidIdentifierError as exc:
        raise create_http_error(
            status.HTTP_401_UNAUTHORIZED,
            code="invalid_credentials",
            message=str(exc),
        ) from exc
    except InvalidCredentialsError as exc:
        raise create_http_error(
            status.HTTP_401_UNAUTHORIZED,
            code="invalid_credentials",
            message=str(exc),
        ) from exc
    except EmailVerificationRequiredError as exc:
        raise create_http_error(
            status.HTTP_403_FORBIDDEN,
            code="email_verification_required",
            message=str(exc),
        ) from exc

    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
        refresh_expires_in=result.refresh_expires_in,
        user=UserResponse.model_validate(result.user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh authentication tokens",
    responses=ERROR_RESPONSES,
)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    service: AuthServiceDependency,
    repository: UserRepositoryDependency,
) -> TokenResponse:
    try:
        result = await service.refresh_authentication(
            repository,
            refresh_token=payload.refresh_token,
        )
    except ExpiredTokenError as exc:
        raise create_http_error(
            status.HTTP_401_UNAUTHORIZED,
            code="invalid_token",
            message="Refresh token has expired.",
        ) from exc
    except (
        InvalidTokenError,
        CurrentUserNotFoundError,
        InactiveUserError,
    ) as exc:
        raise create_http_error(
            status.HTTP_401_UNAUTHORIZED,
            code="invalid_token",
            message="Refresh token is invalid.",
        ) from exc
    except EmailVerificationRequiredError as exc:
        raise create_http_error(
            status.HTTP_403_FORBIDDEN,
            code="email_verification_required",
            message=str(exc),
        ) from exc

    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
        refresh_expires_in=result.refresh_expires_in,
        user=UserResponse.model_validate(result.user),
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout the current user",
    responses=ERROR_RESPONSES,
)
async def logout_user(
    _: AuthenticatedUserDependency,
) -> MessageResponse:
    return MessageResponse(
        message="Logout completed. Discard existing client tokens."
    )


@router.post(
    "/password-reset/request",
    response_model=ActionTokenResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a password reset flow",
    responses=ERROR_RESPONSES,
)
async def request_password_reset(
    payload: PasswordResetRequest,
    service: AuthServiceDependency,
    repository: UserRepositoryDependency,
) -> ActionTokenResponse:
    try:
        result = await service.issue_password_reset_token(
            repository,
            identifier=payload.identifier,
        )
    except InvalidIdentifierError as exc:
        raise create_http_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="validation_error",
            message="Invalid password reset request.",
            fields=[{"field": "identifier", "message": str(exc)}],
        ) from exc

    return ActionTokenResponse(
        message=result.message,
        token=result.token,
        expires_in=result.expires_in,
    )


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete a password reset flow",
    responses=ERROR_RESPONSES,
)
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    service: AuthServiceDependency,
    repository: UserRepositoryDependency,
) -> MessageResponse:
    try:
        await service.reset_password(
            repository,
            token=payload.token,
            new_password=payload.new_password.get_secret_value(),
        )
    except ServiceValidationError as exc:
        raise create_http_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="validation_error",
            message=exc.message,
            fields=exc.fields,
        ) from exc
    except ExpiredTokenError as exc:
        raise create_http_error(
            status.HTTP_400_BAD_REQUEST,
            code="expired_token",
            message="Password reset token has expired.",
        ) from exc
    except (
        InvalidTokenError,
        CurrentUserNotFoundError,
        InactiveUserError,
    ) as exc:
        raise create_http_error(
            status.HTTP_400_BAD_REQUEST,
            code="invalid_token",
            message="Password reset token is invalid.",
        ) from exc

    return MessageResponse(message="Password reset completed successfully.")


@router.post(
    "/email-verification/request",
    response_model=ActionTokenResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate an email verification token",
    responses=ERROR_RESPONSES,
)
async def request_email_verification(
    payload: EmailVerificationRequest,
    service: AuthServiceDependency,
    repository: UserRepositoryDependency,
) -> ActionTokenResponse:
    try:
        result = await service.issue_email_verification_token(
            repository,
            identifier=payload.identifier,
        )
    except InvalidIdentifierError as exc:
        raise create_http_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="validation_error",
            message="Invalid email verification request.",
            fields=[{"field": "identifier", "message": str(exc)}],
        ) from exc

    return ActionTokenResponse(
        message=result.message,
        token=result.token,
        expires_in=result.expires_in,
    )


@router.post(
    "/email-verification/confirm",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify a user's email address",
    responses=ERROR_RESPONSES,
)
async def confirm_email_verification(
    payload: EmailVerificationConfirmRequest,
    service: AuthServiceDependency,
    repository: UserRepositoryDependency,
) -> UserResponse:
    try:
        user = await service.verify_email(
            repository,
            token=payload.token,
        )
    except ExpiredTokenError as exc:
        raise create_http_error(
            status.HTTP_400_BAD_REQUEST,
            code="expired_token",
            message="Email verification token has expired.",
        ) from exc
    except (
        InvalidTokenError,
        CurrentUserNotFoundError,
        InactiveUserError,
    ) as exc:
        raise create_http_error(
            status.HTTP_400_BAD_REQUEST,
            code="invalid_token",
            message="Email verification token is invalid.",
        ) from exc

    return UserResponse.model_validate(user)
