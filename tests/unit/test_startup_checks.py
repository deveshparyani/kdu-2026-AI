import pytest

from app.core.config import AppEnv, Settings
from app.core.startup_checks import UnsafeConfigurationError, validate_runtime_settings


def test_validate_runtime_settings_allows_test_environment_defaults() -> None:
    validate_runtime_settings(Settings(APP_ENV=AppEnv.TEST))


def test_validate_runtime_settings_rejects_placeholder_secret_in_production() -> None:
    settings = Settings(
        APP_ENV=AppEnv.PRODUCTION,
        APP_DEBUG=False,
        SECRET_KEY="change-me",
        AUTH_JWT_SECRET="production-jwt-secret-key",
    )

    with pytest.raises(UnsafeConfigurationError):
        validate_runtime_settings(settings)


def test_validate_runtime_settings_rejects_debug_mode_in_staging() -> None:
    settings = Settings(
        APP_ENV=AppEnv.STAGING,
        APP_DEBUG=True,
        SECRET_KEY="staging-secret-key",
        AUTH_JWT_SECRET="staging-jwt-secret-key",
    )

    with pytest.raises(UnsafeConfigurationError):
        validate_runtime_settings(settings)


def test_validate_runtime_settings_accepts_safe_production_settings() -> None:
    validate_runtime_settings(
        Settings(
            APP_ENV=AppEnv.PRODUCTION,
            APP_DEBUG=False,
            SECRET_KEY="production-secret-key",
            AUTH_JWT_SECRET="production-jwt-secret-key",
        )
    )
