import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    groq_api_key: str | None
    openweathermap_api_key: str | None
    database_url: str
    text_model: str
    vision_model: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv(ROOT_DIR / ".env")

    return Settings(
        app_name=os.getenv("APP_NAME", "Multimodal Assistant API"),
        app_env=os.getenv("APP_ENV", "development"),
        groq_api_key=os.getenv("GROQ_API_KEY"),
        openweathermap_api_key=os.getenv("OPENWEATHERMAP_API_KEY"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://assistant_user:assistant_pass@localhost:5433/assistant_db",
        ),
        text_model=os.getenv("TEXT_MODEL", "llama-3.3-70b-versatile"),
        vision_model=os.getenv(
            "VISION_MODEL",
            "meta-llama/llama-4-scout-17b-16e-instruct",
        ),
    )
