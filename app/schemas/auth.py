from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from app.schemas.user import UserResponse


class RegistrationRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "StrongPass123!",
                },
                {
                    "username": "template_user",
                    "password": "StrongPass123!",
                },
            ]
        }
    )

    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: SecretStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: Optional[EmailStr]) -> Optional[str]:
        if value is None:
            return None
        return str(value).lower()

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "identifier": "user@example.com",
                    "password": "StrongPass123!",
                },
                {
                    "identifier": "template_user",
                    "password": "StrongPass123!",
                },
            ]
        }
    )

    identifier: str = Field(min_length=1, max_length=320)
    password: SecretStr

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Identifier must not be empty.")
        return normalized


class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "refresh.jwt.token",
            }
        }
    )

    refresh_token: str = Field(min_length=1)


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "identifier": "user@example.com",
                },
                {
                    "identifier": "template_user",
                },
            ]
        }
    )

    identifier: str = Field(min_length=1, max_length=320)

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Identifier must not be empty.")
        return normalized


class EmailVerificationRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "identifier": "user@example.com",
                },
                {
                    "identifier": "template_user",
                },
            ]
        }
    )

    identifier: str = Field(min_length=1, max_length=320)

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Identifier must not be empty.")
        return normalized


class PasswordResetConfirmRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "password.reset.token",
                "new_password": "NewStrongPass123!",
            }
        }
    )

    token: str = Field(min_length=1)
    new_password: SecretStr


class EmailVerificationConfirmRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "email.verification.token",
            }
        }
    )

    token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "access_token": "access.jwt.token",
                "refresh_token": "refresh.jwt.token",
                "token_type": "bearer",
                "expires_in": 900,
                "refresh_expires_in": 604800,
                "user": {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "email": "user@example.com",
                    "username": "template_user",
                    "role": "user",
                    "is_active": True,
                    "is_verified": False,
                },
            }
        },
    )

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    refresh_expires_in: int
    user: UserResponse


class ActionTokenResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Password reset instructions have been generated.",
                "token": "password.reset.token",
                "expires_in": 3600,
            }
        }
    )

    message: str
    token: Optional[str] = None
    expires_in: Optional[int] = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Operation completed successfully.",
            }
        }
    )

    message: str


class AccessContextResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Admin access granted.",
                "user": {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "email": "admin@example.com",
                    "username": "admin_user",
                    "role": "admin",
                    "is_active": True,
                    "is_verified": False,
                },
            }
        }
    )

    message: str
    user: UserResponse
