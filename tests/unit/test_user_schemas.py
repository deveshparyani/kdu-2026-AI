import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.core.config import AuthIdentifierMode, Settings
from app.models.user import User, UserRole
from app.schemas.user import (
    AuthIdentifierInput,
    PasswordPolicy,
    UserCreate,
    UserResponse,
    build_user_schema_context,
)


def test_user_create_requires_email_in_email_mode() -> None:
    settings = Settings(AUTH_IDENTIFIER_MODE=AuthIdentifierMode.EMAIL)
    context = build_user_schema_context(settings)

    user = UserCreate.model_validate(
        {"email": "USER@EXAMPLE.COM", "password": "strongpass"},
        context=context,
    )

    assert user.email == "user@example.com"
    assert user.username is None


def test_user_create_requires_username_in_username_mode() -> None:
    settings = Settings(
        AUTH_IDENTIFIER_MODE=AuthIdentifierMode.USERNAME,
        AUTH_USERNAME_MIN_LENGTH=3,
        AUTH_USERNAME_MAX_LENGTH=32,
        AUTH_USERNAME_REGEX=r"^[a-z0-9_]+$",
    )
    context = build_user_schema_context(settings)

    user = UserCreate.model_validate(
        {"username": "valid_name", "password": "strongpass"},
        context=context,
    )

    assert user.username == "valid_name"
    assert user.email is None


def test_user_create_accepts_either_identifier_mode() -> None:
    settings = Settings(AUTH_IDENTIFIER_MODE=AuthIdentifierMode.EITHER)
    context = build_user_schema_context(settings)

    user = UserCreate.model_validate(
        {"username": "template_user", "password": "strongpass"},
        context=context,
    )

    assert user.username == "template_user"


def test_user_create_supports_password_policy_context() -> None:
    with pytest.raises(ValidationError):
        UserCreate.model_validate(
            {"email": "user@example.com", "password": "alllowercase"},
            context={
                "auth_identifier_mode": AuthIdentifierMode.EMAIL,
                "password_policy": PasswordPolicy(
                    min_length=8,
                    require_uppercase=True,
                    require_digit=True,
                ),
            },
        )


def test_auth_identifier_input_is_reusable_for_either_mode() -> None:
    schema = AuthIdentifierInput.model_validate(
        {"identifier": "USER@EXAMPLE.COM"},
        context={"auth_identifier_mode": AuthIdentifierMode.EITHER},
    )

    assert schema.identifier == "user@example.com"


def test_user_response_excludes_password_hash() -> None:
    user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        username="template_user",
        password_hash="not-exposed",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    response = UserResponse.model_validate(user)

    assert response.model_dump(mode="json") == {
        "id": str(user.id),
        "email": "user@example.com",
        "username": "template_user",
        "role": UserRole.ADMIN.value,
        "is_active": True,
        "is_verified": False,
    }
