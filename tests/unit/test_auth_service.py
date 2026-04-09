from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.core.config import AppEnv, AuthIdentifierMode, Settings
from app.models.user import User, UserRole
from app.services.auth import (
    AuthService,
    CurrentUserNotFoundError,
    DuplicateUserError,
    EmailVerificationRequiredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidIdentifierError,
    RegistrationDisabledError,
    ServiceValidationError,
)


class FakeCurrentUserRepository:
    def __init__(self, user: User | None) -> None:
        self._user = user

    async def get_by_id(self, user_id: UUID) -> User | None:
        if self._user and self._user.id == user_id:
            return self._user
        return None


class FakeAuthUserRepository(FakeCurrentUserRepository):
    def __init__(self) -> None:
        super().__init__(None)
        self._users_by_id: dict[UUID, User] = {}

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._users_by_id.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next(
            (user for user in self._users_by_id.values() if user.email == email),
            None,
        )

    async def get_by_username(self, username: str) -> User | None:
        return next(
            (user for user in self._users_by_id.values() if user.username == username),
            None,
        )

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
        user = User(
            id=uuid4(),
            email=email,
            username=username,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
            is_verified=is_verified,
        )
        self._users_by_id[user.id] = user
        return user

    async def update_password_hash(
        self,
        user: User,
        *,
        password_hash: str,
    ) -> User:
        user.password_hash = password_hash
        self._users_by_id[user.id] = user
        return user

    async def set_email_verified(
        self,
        user: User,
        *,
        is_verified: bool = True,
    ) -> User:
        user.is_verified = is_verified
        self._users_by_id[user.id] = user
        return user


def test_identifier_lookup_supports_email_mode() -> None:
    service = AuthService(
        Settings(
            AUTH_IDENTIFIER_MODE=AuthIdentifierMode.EMAIL,
            AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
        )
    )

    lookup = service.build_identifier_lookup("USER@EXAMPLE.COM")

    assert lookup.field == "email"
    assert lookup.value == "user@example.com"


def test_identifier_lookup_supports_either_mode() -> None:
    service = AuthService(
        Settings(
            AUTH_IDENTIFIER_MODE=AuthIdentifierMode.EITHER,
            AUTH_USERNAME_REGEX=r"^[a-z0-9_]+$",
            AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
        )
    )

    lookup = service.build_identifier_lookup("valid_name")

    assert lookup.field == "username"
    assert lookup.value == "valid_name"


def test_identifier_lookup_rejects_invalid_username() -> None:
    service = AuthService(
        Settings(
            AUTH_IDENTIFIER_MODE=AuthIdentifierMode.USERNAME,
            AUTH_USERNAME_REGEX=r"^[a-z0-9_]+$",
            AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
        )
    )

    with pytest.raises(InvalidIdentifierError):
        service.build_identifier_lookup("Not Allowed!")


@pytest.mark.anyio
async def test_resolve_current_user_returns_matching_user() -> None:
    user = User(
        id=uuid4(),
        email="user@example.com",
        username="template_user",
        password_hash="hash",
        role=UserRole.USER,
        is_active=True,
        is_verified=False,
    )
    settings = Settings(
        AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
        AUTH_JWT_ISSUER="test-suite",
        AUTH_JWT_AUDIENCE="test-clients",
    )
    service = AuthService(settings)
    token = service.create_access_token(user.id)

    resolved_user = await service.resolve_current_user(
        token,
        FakeCurrentUserRepository(user),
    )

    assert resolved_user.id == user.id


@pytest.mark.anyio
async def test_resolve_current_user_rejects_missing_user() -> None:
    settings = Settings(
        AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
        AUTH_JWT_ISSUER="test-suite",
        AUTH_JWT_AUDIENCE="test-clients",
    )
    service = AuthService(settings)
    token = service.create_access_token(uuid4())

    with pytest.raises(CurrentUserNotFoundError):
        await service.resolve_current_user(token, FakeCurrentUserRepository(None))


@pytest.mark.anyio
async def test_resolve_current_user_rejects_inactive_user() -> None:
    user = User(
        id=uuid4(),
        email="user@example.com",
        username="template_user",
        password_hash="hash",
        role=UserRole.USER,
        is_active=False,
        is_verified=False,
    )
    settings = Settings(
        AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
        AUTH_JWT_ISSUER="test-suite",
        AUTH_JWT_AUDIENCE="test-clients",
    )
    service = AuthService(settings)
    token = service.create_access_token(user.id)

    with pytest.raises(InactiveUserError):
        await service.resolve_current_user(token, FakeCurrentUserRepository(user))


@pytest.mark.anyio
async def test_register_user_hashes_password_and_persists_normalized_email() -> None:
    repository = FakeAuthUserRepository()
    service = AuthService(
        Settings(
            AUTH_IDENTIFIER_MODE=AuthIdentifierMode.EMAIL,
            AUTH_PASSWORD_MIN_LENGTH=8,
            AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
        )
    )

    user = await service.register_user(
        repository,
        email="USER@EXAMPLE.COM",
        username=None,
        password="StrongPass123!",
    )

    assert user.email == "user@example.com"
    assert user.password_hash != "StrongPass123!"
    assert service.verify_password("StrongPass123!", user.password_hash)


@pytest.mark.anyio
async def test_register_user_rejects_duplicate_email() -> None:
    repository = FakeAuthUserRepository()
    service = AuthService(
        Settings(
            AUTH_IDENTIFIER_MODE=AuthIdentifierMode.EMAIL,
            AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
        )
    )
    await repository.create(
        email="user@example.com",
        username=None,
        password_hash="hash",
        role=UserRole.USER,
    )

    with pytest.raises(DuplicateUserError):
        await service.register_user(
            repository,
            email="user@example.com",
            username=None,
            password="StrongPass123!",
        )


@pytest.mark.anyio
async def test_register_user_supports_username_mode() -> None:
    repository = FakeAuthUserRepository()
    service = AuthService(
        Settings(
            AUTH_IDENTIFIER_MODE=AuthIdentifierMode.USERNAME,
            AUTH_USERNAME_REGEX=r"^[a-z0-9_]+$",
            AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
        )
    )

    user = await service.register_user(
        repository,
        email=None,
        username="valid_name",
        password="StrongPass123!",
    )

    assert user.username == "valid_name"
    assert user.email is None


@pytest.mark.anyio
async def test_register_user_rejects_weak_password() -> None:
    repository = FakeAuthUserRepository()
    service = AuthService(
        Settings(
            AUTH_IDENTIFIER_MODE=AuthIdentifierMode.EMAIL,
            AUTH_PASSWORD_MIN_LENGTH=12,
            AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
        )
    )

    with pytest.raises(ServiceValidationError):
        await service.register_user(
            repository,
            email="user@example.com",
            username=None,
            password="short",
        )


@pytest.mark.anyio
async def test_register_user_respects_registration_disabled_setting() -> None:
    repository = FakeAuthUserRepository()
    service = AuthService(
        Settings(
            AUTH_ALLOW_SELF_SIGNUP=False,
            AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
        )
    )

    with pytest.raises(RegistrationDisabledError):
        await service.register_user(
            repository,
            email="blocked@example.com",
            username=None,
            password="StrongPass123!",
        )


@pytest.mark.anyio
async def test_authenticate_user_returns_token_bundle_for_valid_credentials() -> None:
    repository = FakeAuthUserRepository()
    service = AuthService(
        Settings(
            AUTH_IDENTIFIER_MODE=AuthIdentifierMode.EMAIL,
            AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
            AUTH_JWT_ISSUER="test-suite",
            AUTH_JWT_AUDIENCE="test-clients",
        )
    )
    user = await repository.create(
        email="user@example.com",
        username=None,
        password_hash=service.hash_password("StrongPass123!"),
        role=UserRole.USER,
        is_verified=True,
    )

    result = await service.authenticate_user(
        repository,
        identifier="user@example.com",
        password="StrongPass123!",
    )

    assert result.user.id == user.id
    assert result.access_token
    assert result.refresh_token
    assert result.token_type == "bearer"


@pytest.mark.anyio
async def test_authenticate_user_rejects_invalid_password() -> None:
    repository = FakeAuthUserRepository()
    service = AuthService(
        Settings(
            AUTH_IDENTIFIER_MODE=AuthIdentifierMode.EMAIL,
            AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
        )
    )
    await repository.create(
        email="user@example.com",
        username=None,
        password_hash=service.hash_password("StrongPass123!"),
        role=UserRole.USER,
        is_verified=True,
    )

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate_user(
            repository,
            identifier="user@example.com",
            password="WrongPassword123!",
        )


@pytest.mark.anyio
async def test_authenticate_user_rejects_unverified_user_when_required() -> None:
    repository = FakeAuthUserRepository()
    service = AuthService(
        Settings(
            AUTH_REQUIRE_EMAIL_VERIFICATION=True,
            AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
        )
    )
    await repository.create(
        email="verify@example.com",
        username=None,
        password_hash=service.hash_password("StrongPass123!"),
        role=UserRole.USER,
        is_verified=False,
    )

    with pytest.raises(EmailVerificationRequiredError):
        await service.authenticate_user(
            repository,
            identifier="verify@example.com",
            password="StrongPass123!",
        )


@pytest.mark.anyio
async def test_refresh_authentication_rotates_refresh_token_when_enabled() -> None:
    repository = FakeAuthUserRepository()
    settings = Settings(
        AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
        AUTH_JWT_ISSUER="test-suite",
        AUTH_JWT_AUDIENCE="test-clients",
        AUTH_REFRESH_TOKEN_ROTATION=True,
    )
    service = AuthService(settings)
    user = await repository.create(
        email="refresh@example.com",
        username=None,
        password_hash=service.hash_password("StrongPass123!"),
        role=UserRole.USER,
        is_verified=True,
    )
    original_refresh_token = service.create_refresh_token(user.id)

    result = await service.refresh_authentication(
        repository,
        refresh_token=original_refresh_token,
    )

    assert result.access_token
    assert result.refresh_token != original_refresh_token


@pytest.mark.anyio
async def test_password_reset_flow_updates_password_hash() -> None:
    repository = FakeAuthUserRepository()
    settings = Settings(
        APP_ENV=AppEnv.TEST,
        AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
        AUTH_JWT_ISSUER="test-suite",
        AUTH_JWT_AUDIENCE="test-clients",
    )
    service = AuthService(settings)
    user = await repository.create(
        email="reset@example.com",
        username=None,
        password_hash=service.hash_password("StrongPass123!"),
        role=UserRole.USER,
    )

    issued = await service.issue_password_reset_token(
        repository,
        identifier="reset@example.com",
    )
    assert issued.token is not None

    updated_user = await service.reset_password(
        repository,
        token=issued.token,
        new_password="NewStrongPass123!",
    )

    assert updated_user.id == user.id
    assert service.verify_password("NewStrongPass123!", updated_user.password_hash)


@pytest.mark.anyio
async def test_email_verification_flow_marks_user_verified() -> None:
    repository = FakeAuthUserRepository()
    settings = Settings(
        APP_ENV=AppEnv.TEST,
        AUTH_JWT_SECRET="super-secret-test-key-with-32-chars",
        AUTH_JWT_ISSUER="test-suite",
        AUTH_JWT_AUDIENCE="test-clients",
    )
    service = AuthService(settings)
    user = await repository.create(
        email="verify@example.com",
        username=None,
        password_hash=service.hash_password("StrongPass123!"),
        role=UserRole.USER,
        is_verified=False,
    )

    issued = await service.issue_email_verification_token(
        repository,
        identifier="verify@example.com",
    )
    assert issued.token is not None

    verified_user = await service.verify_email(
        repository,
        token=issued.token,
    )

    assert verified_user.id == user.id
    assert verified_user.is_verified is True
