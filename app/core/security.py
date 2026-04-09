from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, cast
from uuid import UUID, uuid4

import jwt
from passlib.context import CryptContext  # type: ignore[import-untyped]
from passlib.exc import UnknownHashError  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings, get_settings


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"


class SecurityError(Exception):
    """Base auth/security error."""


class UnsupportedPasswordHashSchemeError(SecurityError):
    """Raised when the configured password hash scheme is not supported."""


class InvalidTokenError(SecurityError):
    """Raised when a token is invalid or cannot be decoded."""


class ExpiredTokenError(InvalidTokenError):
    """Raised when a token has expired."""


class MissingTokenConfigurationError(SecurityError):
    """Raised when token signing configuration is incomplete."""


class TokenClaims(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    subject: str = Field(alias="sub")
    token_type: TokenType = Field(alias="type")
    issuer: str = Field(alias="iss")
    audience: str = Field(alias="aud")
    issued_at: int = Field(alias="iat")
    expires_at: int = Field(alias="exp")


class SecurityManager:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._password_context = self._build_password_context(self._settings)

    def hash_password(self, password: str) -> str:
        if not password:
            raise ValueError("Password must not be empty.")
        return cast(str, self._password_context.hash(password))

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            return cast(bool, self._password_context.verify(password, password_hash))
        except (ValueError, UnknownHashError):
            return False

    def create_access_token(
        self,
        subject: UUID | str,
        additional_claims: Mapping[str, Any] | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        return self.create_token(
            subject=subject,
            token_type=TokenType.ACCESS,
            expires_delta=expires_delta or self._settings.auth_access_token_ttl,
            additional_claims=additional_claims,
        )

    def create_refresh_token(
        self,
        subject: UUID | str,
        additional_claims: Mapping[str, Any] | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        return self.create_token(
            subject=subject,
            token_type=TokenType.REFRESH,
            expires_delta=expires_delta or self._settings.auth_refresh_token_ttl,
            additional_claims=additional_claims,
        )

    def create_password_reset_token(
        self,
        subject: UUID | str,
        additional_claims: Mapping[str, Any] | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        return self.create_token(
            subject=subject,
            token_type=TokenType.PASSWORD_RESET,
            expires_delta=(
                expires_delta or self._settings.auth_password_reset_token_ttl
            ),
            additional_claims=additional_claims,
        )

    def create_email_verification_token(
        self,
        subject: UUID | str,
        additional_claims: Mapping[str, Any] | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        return self.create_token(
            subject=subject,
            token_type=TokenType.EMAIL_VERIFICATION,
            expires_delta=(
                expires_delta or self._settings.auth_email_verification_token_ttl
            ),
            additional_claims=additional_claims,
        )

    def create_token(
        self,
        subject: UUID | str,
        token_type: TokenType,
        expires_delta: timedelta,
        additional_claims: Mapping[str, Any] | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        expires_at = now + expires_delta
        payload: dict[str, Any] = {
            "sub": str(subject),
            "jti": str(uuid4()),
            "type": token_type.value,
            "iss": self._settings.auth_jwt_issuer,
            "aud": self._settings.auth_jwt_audience,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        if additional_claims:
            payload.update(dict(additional_claims))

        return jwt.encode(
            payload,
            self._get_jwt_encode_key(),
            algorithm=self._settings.auth_jwt_algorithm,
        )

    def decode_token(
        self,
        token: str,
        expected_token_type: TokenType | None = None,
    ) -> TokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._get_jwt_decode_key(),
                algorithms=[self._settings.auth_jwt_algorithm],
                audience=self._settings.auth_jwt_audience,
                issuer=self._settings.auth_jwt_issuer,
            )
            claims = TokenClaims.model_validate(payload)
        except jwt.ExpiredSignatureError as exc:
            raise ExpiredTokenError("Token has expired.") from exc
        except (jwt.InvalidTokenError, ValidationError) as exc:
            raise InvalidTokenError("Token is invalid.") from exc

        if expected_token_type and claims.token_type != expected_token_type:
            raise InvalidTokenError("Token type is invalid for this operation.")

        return claims

    def _build_password_context(self, settings: Settings) -> CryptContext:
        scheme = settings.auth_password_hash_scheme.strip().lower()

        if scheme in {"argon2", "argon2id"}:
            return CryptContext(
                schemes=["argon2"],
                deprecated="auto",
                argon2__type="ID",
            )
        if scheme == "bcrypt":
            return CryptContext(
                schemes=["bcrypt"],
                deprecated="auto",
                bcrypt__rounds=settings.auth_bcrypt_rounds,
            )

        raise UnsupportedPasswordHashSchemeError(
            f"Unsupported password hash scheme: {settings.auth_password_hash_scheme}"
        )

    def _get_jwt_encode_key(self) -> str:
        algorithm = self._settings.auth_jwt_algorithm.upper()

        if algorithm.startswith("HS"):
            if not self._settings.auth_jwt_secret:
                raise MissingTokenConfigurationError(
                    "AUTH_JWT_SECRET must be configured for HMAC algorithms."
                )
            return self._settings.auth_jwt_secret

        if not self._settings.auth_jwt_private_key:
            raise MissingTokenConfigurationError(
                "AUTH_JWT_PRIVATE_KEY must be configured for asymmetric algorithms."
            )
        return self._settings.auth_jwt_private_key

    def _get_jwt_decode_key(self) -> str:
        algorithm = self._settings.auth_jwt_algorithm.upper()

        if algorithm.startswith("HS"):
            if not self._settings.auth_jwt_secret:
                raise MissingTokenConfigurationError(
                    "AUTH_JWT_SECRET must be configured for HMAC algorithms."
                )
            return self._settings.auth_jwt_secret

        if self._settings.auth_jwt_public_key:
            return self._settings.auth_jwt_public_key
        if self._settings.auth_jwt_private_key:
            return self._settings.auth_jwt_private_key

        raise MissingTokenConfigurationError(
            "AUTH_JWT_PUBLIC_KEY or AUTH_JWT_PRIVATE_KEY must be configured for "
            "asymmetric algorithms."
        )
