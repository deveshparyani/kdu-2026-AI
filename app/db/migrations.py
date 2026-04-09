from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from alembic import command


def upgrade_database_head(database_url: str) -> None:
    config = Config(str(_project_root() / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", resolve_migration_database_url(database_url))
    command.upgrade(config, "head")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_migration_database_url(database_url: str) -> str:
    if database_url.startswith("sqlite+aiosqlite://"):
        return database_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    return database_url
