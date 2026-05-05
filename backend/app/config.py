"""Why this file exists: it keeps environment-based settings in one place."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Small settings object for the local FastAPI backend."""

    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ChatKit Travel Agent Backend"
    environment: str = "development"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-nano"
    frontend_origin: str = "http://localhost:3000"
    demo_default_user_id: str = "demo-user"
    chatkit_workflow_id: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings object for the app."""

    return Settings()
