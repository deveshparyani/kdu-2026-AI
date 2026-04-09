from __future__ import annotations

from app.core.config import AppEnv, Settings

PLACEHOLDER_SECRETS = {"", "change-me"}


class UnsafeConfigurationError(RuntimeError):
    """Raised when runtime settings are unsafe for the target environment."""


def validate_runtime_settings(settings: Settings) -> None:
    if settings.app_env not in {AppEnv.STAGING, AppEnv.PRODUCTION}:
        return

    if settings.app_debug:
        raise UnsafeConfigurationError(
            "APP_DEBUG must be disabled in staging and production."
        )

    if settings.secret_key.strip() in PLACEHOLDER_SECRETS:
        raise UnsafeConfigurationError(
            "SECRET_KEY must be configured with a non-placeholder value."
        )

    algorithm = settings.auth_jwt_algorithm.upper()
    if algorithm.startswith("HS") and settings.auth_jwt_secret.strip() in (
        PLACEHOLDER_SECRETS
    ):
        raise UnsafeConfigurationError(
            "AUTH_JWT_SECRET must be configured with a non-placeholder value for "
            "HMAC algorithms."
        )
