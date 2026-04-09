from __future__ import annotations

from fastapi import FastAPI

from app.api.router import build_api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.lifecycle import create_lifespan
from app.core.middleware import register_middleware
from app.core.startup_checks import validate_runtime_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    validate_runtime_settings(resolved_settings)
    contact = _build_contact_metadata(resolved_settings)
    license_info = _build_license_metadata(resolved_settings)

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description=resolved_settings.app_description,
        debug=resolved_settings.app_debug,
        terms_of_service=resolved_settings.app_terms_of_service_url or None,
        contact=contact,
        license_info=license_info,
        openapi_tags=_build_openapi_tags(),
        servers=[
            {
                "url": resolved_settings.app_base_url,
                "description": f"{resolved_settings.app_env.value} base URL",
            }
        ],
        openapi_url=(
            resolved_settings.openapi_url
            if resolved_settings.feature_docs_enabled
            else None
        ),
        docs_url=resolved_settings.docs_url
        if resolved_settings.feature_docs_enabled
        else None,
        redoc_url=resolved_settings.redoc_url
        if resolved_settings.feature_docs_enabled
        else None,
        lifespan=create_lifespan(resolved_settings),
    )
    app.state.settings = resolved_settings
    register_middleware(app, resolved_settings)
    register_exception_handlers(app)
    app.include_router(build_api_router(resolved_settings))
    return app


def _build_contact_metadata(settings: Settings) -> dict[str, str] | None:
    contact: dict[str, str] = {}
    if settings.app_contact_name:
        contact["name"] = settings.app_contact_name
    if settings.app_contact_email:
        contact["email"] = settings.app_contact_email
    if settings.app_contact_url:
        contact["url"] = settings.app_contact_url
    return contact or None


def _build_license_metadata(settings: Settings) -> dict[str, str] | None:
    license_info: dict[str, str] = {}
    if settings.app_license_name:
        license_info["name"] = settings.app_license_name
    if settings.app_license_url:
        license_info["url"] = settings.app_license_url
    return license_info or None


def _build_openapi_tags() -> list[dict[str, str]]:
    return [
        {
            "name": "auth",
            "description": (
                "Registration, login, and authenticated access flows built on the "
                "template's reusable auth service."
            ),
        },
        {
            "name": "health",
            "description": "Operational health and readiness endpoints.",
        },
    ]


app = create_app()
