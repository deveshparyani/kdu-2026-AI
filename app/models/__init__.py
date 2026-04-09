"""ORM model package.

Import ORM models here as they are added so Alembic autogenerate can discover
the shared SQLAlchemy metadata.
"""

from app.models.user import User, UserRole

__all__ = ["User", "UserRole"]
