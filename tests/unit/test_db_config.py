from app.core.config import Settings


def test_database_connect_args_include_timeouts() -> None:
    settings = Settings(
        DATABASE_CONNECT_TIMEOUT=12,
        DATABASE_STATEMENT_TIMEOUT_MS=45_000,
    )

    assert settings.database_connect_args == {
        "connect_timeout": 12,
        "options": "-c statement_timeout=45000",
    }


def test_test_database_url_placeholder_is_available() -> None:
    settings = Settings()

    assert settings.test_database_url.endswith("fastapi_template_test")
    assert settings.test_database_url.startswith("postgresql+psycopg://")
