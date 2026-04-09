from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.config import AppEnv, AuthIdentifierMode, Settings, get_settings
from app.core.security import InvalidTokenError, SecurityManager, TokenClaims, TokenType
from app.models.user import User, UserRole
from app.repositories.user import DuplicateUserRepositoryError
from app.schemas.user import (
    PasswordPolicy,
    UserCreate,
    build_user_schema_context,
    validate_password_against_policy,
)

EMAIL_ADAPTER = TypeAdapter(EmailStr)


class AuthServiceError(Exception):
    """Base auth service error."""


class InvalidIdentifierError(AuthServiceError):
    """Raised when an identifier does not satisfy the configured auth mode."""


class CurrentUserNotFoundError(AuthServiceError):
    """Raised when a token resolves to a non-existent user."""


class InactiveUserError(AuthServiceError):
    """Raised when a resolved user is inactive."""


class DuplicateUserError(AuthServiceError):
    """Raised when a user already exists for a unique identifier."""


class InvalidCredentialsError(AuthServiceError):
    """Raised when login credentials are invalid."""


class RegistrationDisabledError(AuthServiceError):
    """Raised when self-service registration is disabled."""


class EmailVerificationRequiredError(AuthServiceError):
    """Raised when a user must verify their email before continuing."""


@dataclass(frozen=True)
class ServiceValidationError(AuthServiceError):
    message: str
    fields: list[dict[str, str]]


@dataclass(frozen=True)
class IdentifierLookup:
    field: str
    value: str


@dataclass(frozen=True)
class AuthenticationResult:
    user: User
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    refresh_expires_in: int


@dataclass(frozen=True)
class ActionTokenResult:
    message: str
    token: str | None
    expires_in: int | None


class AuthUserRepository(Protocol):
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return a user by id, or None if it does not exist."""

    async def get_by_email(self, email: str) -> User | None:
        """Return a user by email, or None if it does not exist."""

    async def get_by_username(self, username: str) -> User | None:
        """Return a user by username, or None if it does not exist."""

    async def create(
        self,
        *,
        email: str | None,
        username: str | None,
        password_hash: str,
        role: UserRole,
        is_active: bool = True,
        is_verified: bool = False,
    ) -> User:
        """Persist and return a new user."""

    async def update_password_hash(
        self,
        user: User,
        *,
        password_hash: str,
    ) -> User:
        """Persist a new password hash for the user."""

    async def set_email_verified(
        self,
        user: User,
        *,
        is_verified: bool = True,
    ) -> User:
        """Persist an updated verification flag for the user."""


class CurrentUserRepository(Protocol):
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return a user by id, or None if it does not exist."""


class AuthService:
    def __init__(
        self,
        settings: Settings | None = None,
        security_manager: SecurityManager | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._security_manager = security_manager or SecurityManager(self._settings)

    def hash_password(self, password: str) -> str:
        return self._security_manager.hash_password(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        return self._security_manager.verify_password(password, password_hash)

    def create_access_token(
        self,
        subject: UUID | str,
        additional_claims: Mapping[str, Any] | None = None,
    ) -> str:
        return self._security_manager.create_access_token(subject, additional_claims)

    def create_refresh_token(
        self,
        subject: UUID | str,
        additional_claims: Mapping[str, Any] | None = None,
    ) -> str:
        return self._security_manager.create_refresh_token(subject, additional_claims)

    def create_password_reset_token(
        self,
        subject: UUID | str,
        additional_claims: Mapping[str, Any] | None = None,
    ) -> str:
        return self._security_manager.create_password_reset_token(
            subject,
            additional_claims,
        )

    def create_email_verification_token(
        self,
        subject: UUID | str,
        additional_claims: Mapping[str, Any] | None = None,
    ) -> str:
        return self._security_manager.create_email_verification_token(
            subject,
            additional_claims,
        )

    def decode_token(
        self,
        token: str,
        expected_token_type: TokenType | None = None,
    ) -> TokenClaims:
        return self._security_manager.decode_token(
            token,
            expected_token_type=expected_token_type,
        )

    def build_identifier_lookup(self, identifier: str) -> IdentifierLookup:
        normalized = identifier.strip()
        if not normalized:
            raise InvalidIdentifierError("Identifier must not be empty.")

        if self._settings.auth_identifier_mode == AuthIdentifierMode.EMAIL:
            return IdentifierLookup(
                field="email",
                value=self._normalize_email(normalized),
            )

        if self._settings.auth_identifier_mode == AuthIdentifierMode.USERNAME:
            return IdentifierLookup(
                field="username",
                value=self._normalize_username(normalized),
            )

        try:
            return IdentifierLookup(
                field="email",
                value=self._normalize_email(normalized),
            )
        except InvalidIdentifierError:
            return IdentifierLookup(
                field="username",
                value=self._normalize_username(normalized),
            )

    async def resolve_current_user(
        self,
        token: str,
        repository: CurrentUserRepository,
        *,
        require_active: bool = True,
    ) -> User:
        claims = self.decode_token(token, expected_token_type=TokenType.ACCESS)
        user = await self._resolve_user_from_claims(repository, claims)
        if require_active and not user.is_active:
            raise InactiveUserError("Current user is inactive.")
        return user

    async def register_user(
        self,
        repository: AuthUserRepository,
        *,
        email: str | None,
        username: str | None,
        password: str,
        role: UserRole | None = None,
    ) -> User:
        if not self._settings.auth_allow_self_signup:
            raise RegistrationDisabledError("Self-service registration is disabled.")

        resolved_role = role or self._resolve_default_user_role()

        try:
            validated_user = UserCreate.model_validate(
                {
                    "email": email,
                    "username": username,
                    "password": password,
                    "role": resolved_role,
                },
                context=build_user_schema_context(self._settings),
            )
        except ValidationError as exc:
            raise ServiceValidationError(
                message="Invalid registration data.",
                fields=self._build_validation_fields(exc),
            ) from exc

        if validated_user.email is not None:
            existing_email_user = await repository.get_by_email(validated_user.email)
            if existing_email_user is not None:
                raise DuplicateUserError("A user with that email already exists.")

        if validated_user.username is not None:
            existing_username_user = await repository.get_by_username(
                validated_user.username
            )
            if existing_username_user is not None:
                raise DuplicateUserError("A user with that username already exists.")

        try:
            return await repository.create(
                email=validated_user.email,
                username=validated_user.username,
                password_hash=self.hash_password(
                    validated_user.password.get_secret_value()
                ),
                role=validated_user.role,
                is_verified=(
                    not self._settings.auth_require_email_verification
                    or validated_user.email is None
                ),
            )
        except DuplicateUserRepositoryError as exc:
            raise DuplicateUserError(
                "A user with the provided identifier already exists."
            ) from exc

    async def authenticate_user(
        self,
        repository: AuthUserRepository,
        *,
        identifier: str,
        password: str,
    ) -> AuthenticationResult:
        user = await self._get_user_by_identifier(repository, identifier)

        if user is None or not user.is_active:
            raise InvalidCredentialsError("Invalid credentials.")
        if not self.verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid credentials.")

        self._ensure_user_is_verified_for_auth(user)
        return self._issue_authentication_result(user)

    async def refresh_authentication(
        self,
        repository: CurrentUserRepository,
        *,
        refresh_token: str,
    ) -> AuthenticationResult:
        user = await self._resolve_user_from_token(
            refresh_token,
            repository,
            expected_token_type=TokenType.REFRESH,
        )
        self._ensure_user_is_verified_for_auth(user)

        refreshed_token = (
            self.create_refresh_token(
                user.id,
                {"role": user.role.value},
            )
            if self._settings.auth_refresh_token_rotation
            else refresh_token
        )

        return self._issue_authentication_result(
            user,
            refresh_token_override=refreshed_token,
        )

    async def issue_password_reset_token(
        self,
        repository: AuthUserRepository,
        *,
        identifier: str,
    ) -> ActionTokenResult:
        user = await self._get_user_by_identifier(repository, identifier)
        if user is None or not user.is_active:
            return self._build_action_token_result(
                message="Password reset instructions have been generated.",
                token=None,
                expires_in=None,
            )

        token = self.create_password_reset_token(
            user.id,
            {"role": user.role.value},
        )
        return self._build_action_token_result(
            message="Password reset instructions have been generated.",
            token=token,
            expires_in=int(self._settings.auth_password_reset_token_ttl.total_seconds()),
        )

    async def reset_password(
        self,
        repository: AuthUserRepository,
        *,
        token: str,
        new_password: str,
    ) -> User:
        user = await self._resolve_user_from_token(
            token,
            repository,
            expected_token_type=TokenType.PASSWORD_RESET,
        )
        self._validate_password(new_password)
        return await repository.update_password_hash(
            user,
            password_hash=self.hash_password(new_password),
        )

    async def issue_email_verification_token(
        self,
        repository: AuthUserRepository,
        *,
        identifier: str,
    ) -> ActionTokenResult:
        user = await self._get_user_by_identifier(repository, identifier)
        if user is None or not user.is_active or user.email is None or user.is_verified:
            return self._build_action_token_result(
                message="Email verification instructions have been generated.",
                token=None,
                expires_in=None,
            )

        token = self.create_email_verification_token(
            user.id,
            {"email": user.email},
        )
        return self._build_action_token_result(
            message="Email verification instructions have been generated.",
            token=token,
            expires_in=int(
                self._settings.auth_email_verification_token_ttl.total_seconds()
            ),
        )

    async def verify_email(
        self,
        repository: AuthUserRepository,
        *,
        token: str,
    ) -> User:
        claims = self.decode_token(
            token,
            expected_token_type=TokenType.EMAIL_VERIFICATION,
        )
        user = await self._resolve_user_from_claims(repository, claims)
        email_claim = claims.model_extra.get("email") if claims.model_extra else None
        if email_claim is not None and user.email != email_claim:
            raise InvalidTokenError("Token email does not match the current user.")
        return await repository.set_email_verified(user, is_verified=True)

    def _normalize_email(self, identifier: str) -> str:
        try:
            normalized = EMAIL_ADAPTER.validate_python(identifier)
        except ValidationError as exc:
            raise InvalidIdentifierError(
                "Identifier must be a valid email address."
            ) from exc
        return str(normalized).lower()

    def _normalize_username(self, identifier: str) -> str:
        if len(identifier) < self._settings.auth_username_min_length:
            raise InvalidIdentifierError(
                f"Username must be at least {self._settings.auth_username_min_length} "
                "characters."
            )
        if len(identifier) > self._settings.auth_username_max_length:
            raise InvalidIdentifierError(
                f"Username must be at most {self._settings.auth_username_max_length} "
                "characters."
            )
        if not re.fullmatch(self._settings.auth_username_regex, identifier):
            raise InvalidIdentifierError("Identifier must be a valid username.")
        return identifier

    async def _get_user_by_identifier(
        self,
        repository: AuthUserRepository,
        identifier: str,
    ) -> User | None:
        lookup = self.build_identifier_lookup(identifier)
        if lookup.field == "email":
            return await repository.get_by_email(lookup.value)
        return await repository.get_by_username(lookup.value)

    async def _resolve_user_from_token(
        self,
        token: str,
        repository: CurrentUserRepository,
        *,
        expected_token_type: TokenType,
        require_active: bool = True,
    ) -> User:
        claims = self.decode_token(token, expected_token_type=expected_token_type)
        user = await self._resolve_user_from_claims(repository, claims)
        if require_active and not user.is_active:
            raise InactiveUserError("Current user is inactive.")
        return user

    async def _resolve_user_from_claims(
        self,
        repository: CurrentUserRepository,
        claims: TokenClaims,
    ) -> User:
        try:
            user_id = UUID(claims.subject)
        except ValueError as exc:
            raise InvalidTokenError("Token subject is not a valid user id.") from exc

        user = await repository.get_by_id(user_id)
        if user is None:
            raise CurrentUserNotFoundError("Current user could not be resolved.")
        return user

    def _issue_authentication_result(
        self,
        user: User,
        *,
        refresh_token_override: str | None = None,
    ) -> AuthenticationResult:
        return AuthenticationResult(
            user=user,
            access_token=self.create_access_token(
                user.id,
                {"role": user.role.value},
            ),
            refresh_token=refresh_token_override
            or self.create_refresh_token(
                user.id,
                {"role": user.role.value},
            ),
            token_type=self._settings.auth_token_transport,
            expires_in=int(self._settings.auth_access_token_ttl.total_seconds()),
            refresh_expires_in=int(self._settings.auth_refresh_token_ttl.total_seconds()),
        )

    def _resolve_default_user_role(self) -> UserRole:
        try:
            return UserRole(self._settings.default_user_role)
        except ValueError as exc:
            raise ValueError(
                f"Unsupported DEFAULT_USER_ROLE: {self._settings.default_user_role}"
            ) from exc

    def _build_action_token_result(
        self,
        *,
        message: str,
        token: str | None,
        expires_in: int | None,
    ) -> ActionTokenResult:
        if self._settings.app_env not in {AppEnv.DEVELOPMENT, AppEnv.TEST}:
            return ActionTokenResult(message=message, token=None, expires_in=None)
        return ActionTokenResult(message=message, token=token, expires_in=expires_in)

    def _validate_password(self, password: str) -> None:
        context = build_user_schema_context(self._settings)
        policy = context["password_policy"]
        if not isinstance(policy, PasswordPolicy):
            policy = PasswordPolicy()

        try:
            validate_password_against_policy(password, policy)
        except ValueError as exc:
            raise ServiceValidationError(
                message="Invalid password reset data.",
                fields=[{"field": "new_password", "message": f"Value error, {exc}"}],
            ) from exc

    def _ensure_user_is_verified_for_auth(self, user: User) -> None:
        if (
            self._settings.auth_require_email_verification
            and user.email is not None
            and not user.is_verified
        ):
            raise EmailVerificationRequiredError(
                "Email verification is required before continuing."
            )

    def _build_validation_fields(
        self,
        validation_error: ValidationError,
    ) -> list[dict[str, str]]:
        return [
            {
                "field": ".".join(str(part) for part in error["loc"]),
                "message": error["msg"],
            }
            for error in validation_error.errors()
        ]
