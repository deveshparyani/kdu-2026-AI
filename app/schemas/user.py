from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    TypeAdapter,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from app.core.config import AuthIdentifierMode, Settings, get_settings
from app.models.user import UserRole

EMAIL_ADAPTER = TypeAdapter(EmailStr)


@dataclass(frozen=True)
class PasswordPolicy:
    min_length: int = 8
    require_uppercase: bool = False
    require_lowercase: bool = False
    require_digit: bool = False
    require_special: bool = False


def build_user_schema_context(
    settings: Optional[Settings] = None,
) -> dict[str, object]:
    resolved_settings = settings or get_settings()
    return {
        "auth_identifier_mode": resolved_settings.auth_identifier_mode,
        "username_min_length": resolved_settings.auth_username_min_length,
        "username_max_length": resolved_settings.auth_username_max_length,
        "username_regex": resolved_settings.auth_username_regex,
        "password_policy": PasswordPolicy(
            min_length=resolved_settings.auth_password_min_length,
            require_uppercase=resolved_settings.auth_password_require_uppercase,
            require_lowercase=resolved_settings.auth_password_require_lowercase,
            require_digit=resolved_settings.auth_password_require_digit,
            require_special=resolved_settings.auth_password_require_special,
        ),
    }


def _get_identifier_mode(info: ValidationInfo) -> AuthIdentifierMode:
    context = info.context if isinstance(info.context, dict) else {}
    mode = context.get("auth_identifier_mode", AuthIdentifierMode.EMAIL)
    if isinstance(mode, AuthIdentifierMode):
        return mode
    return AuthIdentifierMode(str(mode))


def _get_username_constraints(info: ValidationInfo) -> tuple[int, int, str]:
    context = info.context if isinstance(info.context, dict) else {}
    min_length = int(context.get("username_min_length", 3))
    max_length = int(context.get("username_max_length", 32))
    regex = str(context.get("username_regex", r"^[a-zA-Z0-9_.-]+$"))
    return min_length, max_length, regex


def _get_password_policy(info: ValidationInfo) -> PasswordPolicy:
    context = info.context if isinstance(info.context, dict) else {}
    policy = context.get("password_policy")
    if isinstance(policy, PasswordPolicy):
        return policy
    return PasswordPolicy()


def validate_password_against_policy(
    password: str,
    policy: PasswordPolicy,
) -> None:
    if len(password) < policy.min_length:
        raise ValueError(
            f"Password must be at least {policy.min_length} characters long."
        )
    if policy.require_uppercase and not any(char.isupper() for char in password):
        raise ValueError("Password must include an uppercase letter.")
    if policy.require_lowercase and not any(char.islower() for char in password):
        raise ValueError("Password must include a lowercase letter.")
    if policy.require_digit and not any(char.isdigit() for char in password):
        raise ValueError("Password must include a digit.")
    if policy.require_special and password.isalnum():
        raise ValueError("Password must include a special character.")


class AuthIdentifierInput(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, value: str, info: ValidationInfo) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Identifier must not be empty.")

        mode = _get_identifier_mode(info)
        _, _, username_regex = _get_username_constraints(info)

        if mode == AuthIdentifierMode.EMAIL:
            EMAIL_ADAPTER.validate_python(normalized)
            return normalized.lower()

        if mode == AuthIdentifierMode.USERNAME:
            if not re.fullmatch(username_regex, normalized):
                raise ValueError("Identifier must be a valid username.")
            return normalized

        try:
            EMAIL_ADAPTER.validate_python(normalized)
        except ValidationError:
            if not re.fullmatch(username_regex, normalized):
                raise ValueError(
                    "Identifier must be a valid email address or username."
                ) from None
            return normalized

        return normalized.lower()


class UserCreate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: SecretStr
    role: UserRole = UserRole.USER

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: Optional[EmailStr]) -> Optional[str]:
        if value is None:
            return None
        return str(value).lower()

    @field_validator("username")
    @classmethod
    def validate_username(
        cls,
        value: Optional[str],
        info: ValidationInfo,
    ) -> Optional[str]:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            raise ValueError("Username must not be empty.")

        min_length, max_length, username_regex = _get_username_constraints(info)

        if len(normalized) < min_length:
            raise ValueError(f"Username must be at least {min_length} characters.")
        if len(normalized) > max_length:
            raise ValueError(f"Username must be at most {max_length} characters.")
        if not re.fullmatch(username_regex, normalized):
            raise ValueError("Username contains unsupported characters.")

        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(
        cls,
        value: SecretStr,
        info: ValidationInfo,
    ) -> SecretStr:
        password = value.get_secret_value()
        policy = _get_password_policy(info)
        validate_password_against_policy(password, policy)
        return value

    @model_validator(mode="after")
    def validate_identifier_requirements(self, info: ValidationInfo) -> UserCreate:
        mode = _get_identifier_mode(info)

        if mode == AuthIdentifierMode.EMAIL and not self.email:
            raise ValueError("Email is required when auth identifier mode is email.")
        if mode == AuthIdentifierMode.USERNAME and not self.username:
            raise ValueError(
                "Username is required when auth identifier mode is username."
            )
        if mode == AuthIdentifierMode.EITHER and not (self.email or self.username):
            raise ValueError(
                "Either email or username is required when identifier mode is either."
            )

        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "11111111-1111-1111-1111-111111111111",
                "email": "user@example.com",
                "username": "template_user",
                "role": "user",
                "is_active": True,
                "is_verified": False,
            }
        },
    )

    id: uuid.UUID
    email: Optional[str]
    username: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
