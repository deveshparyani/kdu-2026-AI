from datetime import timedelta
from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class AuthIdentifierMode(str, Enum):
    EMAIL = "email"
    USERNAME = "username"
    EITHER = "either"


class LogFormat(str, Enum):
    PLAIN = "plain"
    JSON = "json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    app_name: str = Field(default="fastapi-template", alias="APP_NAME")
    app_env: AppEnv = Field(default=AppEnv.DEVELOPMENT, alias="APP_ENV")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    app_description: str = Field(
        default=(
            "Reusable FastAPI template with async SQLAlchemy, configurable "
            "authentication, structured logging, and production-oriented "
            "cross-cutting concerns."
        ),
        alias="APP_DESCRIPTION",
    )
    app_terms_of_service_url: str = Field(default="", alias="APP_TERMS_OF_SERVICE_URL")
    app_contact_name: str = Field(default="", alias="APP_CONTACT_NAME")
    app_contact_email: str = Field(default="", alias="APP_CONTACT_EMAIL")
    app_contact_url: str = Field(default="", alias="APP_CONTACT_URL")
    app_license_name: str = Field(default="MIT", alias="APP_LICENSE_NAME")
    app_license_url: str = Field(
        default="https://opensource.org/licenses/MIT",
        alias="APP_LICENSE_URL",
    )
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_base_url: str = Field(default="http://localhost:8000", alias="APP_BASE_URL")
    frontend_base_url: str = Field(
        default="http://localhost:3000",
        alias="FRONTEND_BASE_URL",
    )
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    openapi_url: str = Field(default="/openapi.json", alias="OPENAPI_URL")
    docs_url: str = Field(default="/docs", alias="DOCS_URL")
    redoc_url: str = Field(default="/redoc", alias="REDOC_URL")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    trusted_hosts: str = Field(
        default="localhost,127.0.0.1,testserver",
        alias="TRUSTED_HOSTS",
    )
    cors_allow_origins: str = Field(default="", alias="CORS_ALLOW_ORIGINS")
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: str = Field(default="GET,POST", alias="CORS_ALLOW_METHODS")
    cors_allow_headers: str = Field(default="*", alias="CORS_ALLOW_HEADERS")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/fastapi_template",
        alias="DATABASE_URL",
    )
    test_database_url: str = Field(
        default=(
            "postgresql+psycopg://postgres:postgres@localhost:5432/"
            "fastapi_template_test"
        ),
        alias="TEST_DATABASE_URL",
    )
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")
    database_pool_pre_ping: bool = Field(default=True, alias="DATABASE_POOL_PRE_PING")
    database_pool_timeout: int = Field(default=30, alias="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=1800, alias="DATABASE_POOL_RECYCLE")
    database_connect_timeout: int = Field(default=30, alias="DATABASE_CONNECT_TIMEOUT")
    database_statement_timeout_ms: int = Field(
        default=30_000,
        alias="DATABASE_STATEMENT_TIMEOUT_MS",
    )
    run_migrations_on_startup: bool = Field(
        default=False,
        alias="RUN_MIGRATIONS_ON_STARTUP",
    )
    auth_enabled: bool = Field(default=True, alias="AUTH_ENABLED")
    auth_identifier_mode: AuthIdentifierMode = Field(
        default=AuthIdentifierMode.EMAIL,
        alias="AUTH_IDENTIFIER_MODE",
    )
    auth_allow_self_signup: bool = Field(default=True, alias="AUTH_ALLOW_SELF_SIGNUP")
    auth_require_email_verification: bool = Field(
        default=False,
        alias="AUTH_REQUIRE_EMAIL_VERIFICATION",
    )
    auth_username_min_length: int = Field(default=3, alias="AUTH_USERNAME_MIN_LENGTH")
    auth_username_max_length: int = Field(default=32, alias="AUTH_USERNAME_MAX_LENGTH")
    auth_username_regex: str = Field(
        default=r"^[a-zA-Z0-9_.-]+$",
        alias="AUTH_USERNAME_REGEX",
    )
    auth_password_min_length: int = Field(default=8, alias="AUTH_PASSWORD_MIN_LENGTH")
    auth_password_require_uppercase: bool = Field(
        default=False,
        alias="AUTH_PASSWORD_REQUIRE_UPPERCASE",
    )
    auth_password_require_lowercase: bool = Field(
        default=False,
        alias="AUTH_PASSWORD_REQUIRE_LOWERCASE",
    )
    auth_password_require_digit: bool = Field(
        default=False,
        alias="AUTH_PASSWORD_REQUIRE_DIGIT",
    )
    auth_password_require_special: bool = Field(
        default=False,
        alias="AUTH_PASSWORD_REQUIRE_SPECIAL",
    )
    auth_password_hash_scheme: str = Field(
        default="argon2id",
        alias="AUTH_PASSWORD_HASH_SCHEME",
    )
    auth_bcrypt_rounds: int = Field(default=12, alias="AUTH_BCRYPT_ROUNDS")
    auth_token_transport: str = Field(default="bearer", alias="AUTH_TOKEN_TRANSPORT")
    auth_access_token_ttl_minutes: int = Field(
        default=15,
        alias="AUTH_ACCESS_TOKEN_TTL_MINUTES",
    )
    auth_refresh_token_ttl_minutes: int = Field(
        default=10_080,
        alias="AUTH_REFRESH_TOKEN_TTL_MINUTES",
    )
    auth_refresh_token_rotation: bool = Field(
        default=True,
        alias="AUTH_REFRESH_TOKEN_ROTATION",
    )
    auth_jwt_algorithm: str = Field(default="HS256", alias="AUTH_JWT_ALGORITHM")
    auth_jwt_secret: str = Field(default="change-me", alias="AUTH_JWT_SECRET")
    auth_jwt_private_key: str = Field(default="", alias="AUTH_JWT_PRIVATE_KEY")
    auth_jwt_public_key: str = Field(default="", alias="AUTH_JWT_PUBLIC_KEY")
    auth_jwt_issuer: str = Field(default="fastapi-template", alias="AUTH_JWT_ISSUER")
    auth_jwt_audience: str = Field(
        default="fastapi-template-clients",
        alias="AUTH_JWT_AUDIENCE",
    )
    auth_email_verification_token_ttl_minutes: int = Field(
        default=1_440,
        alias="AUTH_EMAIL_VERIFICATION_TOKEN_TTL_MINUTES",
    )
    auth_password_reset_token_ttl_minutes: int = Field(
        default=60,
        alias="AUTH_PASSWORD_RESET_TOKEN_TTL_MINUTES",
    )
    default_user_role: str = Field(default="user", alias="DEFAULT_USER_ROLE")
    first_superuser_identifier: str = Field(
        default="admin@example.com",
        alias="FIRST_SUPERUSER_IDENTIFIER",
    )
    first_superuser_password: str = Field(
        default="change-me",
        alias="FIRST_SUPERUSER_PASSWORD",
    )
    rate_limit_enabled: bool = Field(default=False, alias="RATE_LIMIT_ENABLED")
    rate_limit_backend: str = Field(default="memory", alias="RATE_LIMIT_BACKEND")
    rate_limit_default: str = Field(default="100/minute", alias="RATE_LIMIT_DEFAULT")
    rate_limit_login: str = Field(default="5/minute", alias="RATE_LIMIT_LOGIN")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    email_enabled: bool = Field(default=False, alias="EMAIL_ENABLED")
    email_from_address: str = Field(
        default="noreply@example.com",
        alias="EMAIL_FROM_ADDRESS",
    )
    email_from_name: str = Field(default="FastAPI Template", alias="EMAIL_FROM_NAME")
    smtp_host: str = Field(default="localhost", alias="SMTP_HOST")
    smtp_port: int = Field(default=1025, alias="SMTP_PORT")
    smtp_username: str = Field(default="", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=False, alias="SMTP_USE_TLS")
    smtp_use_ssl: bool = Field(default=False, alias="SMTP_USE_SSL")
    worker_enabled: bool = Field(default=False, alias="WORKER_ENABLED")
    broker_url: str = Field(default="redis://localhost:6379/1", alias="BROKER_URL")
    result_backend_url: str = Field(
        default="redis://localhost:6379/2",
        alias="RESULT_BACKEND_URL",
    )
    storage_backend: str = Field(default="local", alias="STORAGE_BACKEND")
    storage_local_path: str = Field(default="./storage", alias="STORAGE_LOCAL_PATH")
    s3_bucket: str = Field(default="", alias="S3_BUCKET")
    s3_endpoint_url: str = Field(default="", alias="S3_ENDPOINT_URL")
    aws_access_key_id: str = Field(default="", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", alias="AWS_SECRET_ACCESS_KEY")
    aws_default_region: str = Field(default="us-east-1", alias="AWS_DEFAULT_REGION")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: LogFormat = Field(default=LogFormat.JSON, alias="LOG_FORMAT")
    request_id_header: str = Field(default="X-Request-ID", alias="REQUEST_ID_HEADER")
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    otel_enabled: bool = Field(default=False, alias="OTEL_ENABLED")
    otel_service_name: str = Field(
        default="fastapi-template",
        alias="OTEL_SERVICE_NAME",
    )
    otel_exporter_otlp_endpoint: str = Field(
        default="",
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    feature_healthcheck_enabled: bool = Field(
        default=True,
        alias="FEATURE_HEALTHCHECK_ENABLED",
    )
    feature_docs_enabled: bool = Field(default=True, alias="FEATURE_DOCS_ENABLED")

    @property
    def database_connect_args(self) -> dict[str, object]:
        connect_args: dict[str, object] = {}

        if self.database_connect_timeout > 0:
            connect_args["connect_timeout"] = self.database_connect_timeout

        if self.database_statement_timeout_ms > 0:
            connect_args["options"] = (
                f"-c statement_timeout={self.database_statement_timeout_ms}"
            )

        return connect_args

    @property
    def auth_access_token_ttl(self) -> timedelta:
        return timedelta(minutes=self.auth_access_token_ttl_minutes)

    @property
    def auth_refresh_token_ttl(self) -> timedelta:
        return timedelta(minutes=self.auth_refresh_token_ttl_minutes)

    @property
    def auth_email_verification_token_ttl(self) -> timedelta:
        return timedelta(minutes=self.auth_email_verification_token_ttl_minutes)

    @property
    def auth_password_reset_token_ttl(self) -> timedelta:
        return timedelta(minutes=self.auth_password_reset_token_ttl_minutes)

    @property
    def resolved_log_level(self) -> str:
        if self.log_level.strip():
            return self.log_level
        if self.app_debug or self.app_env in {AppEnv.DEVELOPMENT, AppEnv.TEST}:
            return "DEBUG"
        return "INFO"

    @property
    def trusted_hosts_list(self) -> list[str]:
        return _parse_csv(self.trusted_hosts)

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return _parse_csv(self.cors_allow_origins)

    @property
    def cors_allow_methods_list(self) -> list[str]:
        return _parse_csv(self.cors_allow_methods)

    @property
    def cors_allow_headers_list(self) -> list[str]:
        return _parse_csv(self.cors_allow_headers)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def _parse_csv(value: str) -> list[str]:
    if not value.strip():
        return []
    return [item.strip() for item in value.split(",") if item.strip()]
