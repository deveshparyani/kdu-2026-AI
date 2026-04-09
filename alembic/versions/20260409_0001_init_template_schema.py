"""initial template schema

Revision ID: 20260409_0001
Revises:
Create Date: 2026-04-09 00:00:00.000000
"""

from collections.abc import Sequence
from typing import Optional

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260409_0001"
down_revision: Optional[str] = None
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("username", sa.String(length=32), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "admin", name="user_role", native_enum=False),
            server_default=sa.text("'user'"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "is_verified",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "email IS NOT NULL OR username IS NOT NULL",
            name="users_users_identifier_present_check",
        ),
        sa.PrimaryKeyConstraint("id", name="users_pkey"),
        sa.UniqueConstraint("email", name="users_email_key"),
        sa.UniqueConstraint("username", name="users_username_key"),
    )
    op.create_index("users_email_idx", "users", ["email"], unique=False)
    op.create_index("users_username_idx", "users", ["username"], unique=False)


def downgrade() -> None:
    op.drop_index("users_username_idx", table_name="users")
    op.drop_index("users_email_idx", table_name="users")
    op.drop_table("users")
