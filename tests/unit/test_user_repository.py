import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserRole
from app.repositories.user import DuplicateUserRepositoryError, SQLAlchemyUserRepository

pytestmark = pytest.mark.anyio


async def test_user_repository_persists_and_retrieves_users(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyUserRepository(session=db_session)

    created_user = await repository.create(
        email="persisted@example.com",
        username="persisted_user",
        password_hash="hashed-password",
        role=UserRole.USER,
    )

    fetched_by_id = await repository.get_by_id(created_user.id)
    fetched_by_email = await repository.get_by_email("persisted@example.com")
    fetched_by_username = await repository.get_by_username("persisted_user")

    assert fetched_by_id is not None
    assert fetched_by_id.id == created_user.id
    assert fetched_by_email is not None
    assert fetched_by_email.id == created_user.id
    assert fetched_by_username is not None
    assert fetched_by_username.id == created_user.id


async def test_user_repository_rejects_duplicate_email(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyUserRepository(session=db_session)
    await repository.create(
        email="duplicate@example.com",
        username="unique_name",
        password_hash="hashed-password",
        role=UserRole.USER,
    )

    with pytest.raises(DuplicateUserRepositoryError):
        await repository.create(
            email="duplicate@example.com",
            username="another_name",
            password_hash="hashed-password",
            role=UserRole.USER,
        )


async def test_user_repository_rejects_duplicate_username(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyUserRepository(session=db_session)
    await repository.create(
        email="first@example.com",
        username="shared_name",
        password_hash="hashed-password",
        role=UserRole.USER,
    )

    with pytest.raises(DuplicateUserRepositoryError):
        await repository.create(
            email="second@example.com",
            username="shared_name",
            password_hash="hashed-password",
            role=UserRole.USER,
        )


async def test_user_repository_updates_password_and_verification(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyUserRepository(session=db_session)
    user = await repository.create(
        email="verify@example.com",
        username="verify_user",
        password_hash="old-hash",
        role=UserRole.USER,
        is_verified=False,
    )

    updated_password_user = await repository.update_password_hash(
        user,
        password_hash="new-hash",
    )
    verified_user = await repository.set_email_verified(
        updated_password_user,
        is_verified=True,
    )

    assert verified_user.password_hash == "new-hash"
    assert verified_user.is_verified is True
