from datetime import timedelta
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.security import (
    ExpiredTokenError,
    InvalidTokenError,
    SecurityManager,
    TokenType,
)


def build_security_manager() -> SecurityManager:
    settings = Settings(
        AUTH_PASSWORD_HASH_SCHEME="argon2id",
        AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
        AUTH_JWT_ALGORITHM="HS256",
        AUTH_JWT_ISSUER="test-suite",
        AUTH_JWT_AUDIENCE="test-clients",
        AUTH_ACCESS_TOKEN_TTL_MINUTES=15,
        AUTH_REFRESH_TOKEN_TTL_MINUTES=60,
    )
    return SecurityManager(settings)


def test_hash_password_returns_secure_hash() -> None:
    security = build_security_manager()

    password_hash = security.hash_password("StrongPassword123!")

    assert password_hash != "StrongPassword123!"
    assert security.verify_password("StrongPassword123!", password_hash) is True


def test_verify_password_rejects_invalid_password() -> None:
    security = build_security_manager()
    password_hash = security.hash_password("StrongPassword123!")

    assert security.verify_password("WrongPassword123!", password_hash) is False


def test_create_and_decode_access_token() -> None:
    security = build_security_manager()
    subject = uuid4()

    token = security.create_access_token(subject, {"role": "user"})
    claims = security.decode_token(token, expected_token_type=TokenType.ACCESS)

    assert claims.subject == str(subject)
    assert claims.token_type == TokenType.ACCESS
    assert claims.issuer == "test-suite"
    assert claims.audience == "test-clients"


def test_decode_invalid_token_raises() -> None:
    security = build_security_manager()

    with pytest.raises(InvalidTokenError):
        security.decode_token("not-a-valid-jwt", expected_token_type=TokenType.ACCESS)


def test_decode_expired_token_raises() -> None:
    security = build_security_manager()
    subject = uuid4()
    token = security.create_access_token(
        subject,
        expires_delta=timedelta(minutes=-1),
    )

    with pytest.raises(ExpiredTokenError):
        security.decode_token(token, expected_token_type=TokenType.ACCESS)


def test_refresh_token_is_rejected_when_access_token_is_expected() -> None:
    security = build_security_manager()
    token = security.create_refresh_token(uuid4())

    with pytest.raises(InvalidTokenError):
        security.decode_token(token, expected_token_type=TokenType.ACCESS)


def test_create_and_decode_password_reset_token() -> None:
    security = build_security_manager()
    subject = uuid4()

    token = security.create_password_reset_token(subject)
    claims = security.decode_token(
        token,
        expected_token_type=TokenType.PASSWORD_RESET,
    )

    assert claims.subject == str(subject)
    assert claims.token_type == TokenType.PASSWORD_RESET


def test_create_and_decode_email_verification_token() -> None:
    security = build_security_manager()
    subject = uuid4()

    token = security.create_email_verification_token(
        subject,
        {"email": "user@example.com"},
    )
    claims = security.decode_token(
        token,
        expected_token_type=TokenType.EMAIL_VERIFICATION,
    )

    assert claims.subject == str(subject)
    assert claims.token_type == TokenType.EMAIL_VERIFICATION
    assert claims.model_extra is not None
    assert claims.model_extra["email"] == "user@example.com"


def test_verify_password_rejects_unknown_hash_format() -> None:
    security = build_security_manager()

    assert security.verify_password("StrongPassword123!", "not-a-valid-hash") is False
