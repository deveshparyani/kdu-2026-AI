from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.repositories.base import RepositoryError


class DuplicateUserRepositoryError(RepositoryError):
    """Raised when user creation violates a unique identifier constraint."""


class SQLAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        statement = select(User).where(User.username == username)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

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
            email=email,
            username=username,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
            is_verified=is_verified,
        )
        self._session.add(user)

        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateUserRepositoryError(
                "User with the provided identifier already exists."
            ) from exc

        await self._session.refresh(user)
        return user

    async def update_password_hash(
        self,
        user: User,
        *,
        password_hash: str,
    ) -> User:
        user.password_hash = password_hash
        return await self._commit_and_refresh(user)

    async def set_email_verified(
        self,
        user: User,
        *,
        is_verified: bool = True,
    ) -> User:
        user.is_verified = is_verified
        return await self._commit_and_refresh(user)

    async def _commit_and_refresh(self, user: User) -> User:
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateUserRepositoryError(
                "User update violated a persistence constraint."
            ) from exc

        await self._session.refresh(user)
        return user
