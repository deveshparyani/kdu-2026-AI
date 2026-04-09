from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.core.config import AppEnv, Settings


def build_error_detail(
    code: str,
    message: str,
    fields: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "fields": fields or [],
    }


def create_http_error(
    status_code: int,
    *,
    code: str,
    message: str,
    fields: list[dict[str, str]] | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=build_error_detail(code, message, fields),
    )


def register_exception_handlers(app: FastAPI) -> None:
    logger = logging.getLogger("app.exceptions")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        _: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        detail = exc.detail

        if isinstance(detail, dict) and "code" in detail and "message" in detail:
            payload = {
                "detail": build_error_detail(
                    str(detail["code"]),
                    str(detail["message"]),
                    list(detail.get("fields", [])),
                )
            }
        else:
            payload = {
                "detail": build_error_detail(
                    "http_error",
                    str(detail),
                )
            }

        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        _: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        fields = [
            {
                "field": _format_error_field(error["loc"]),
                "message": error["msg"],
            }
            for error in exc.errors()
        ]

        return JSONResponse(
            status_code=422,
            content={
                "detail": build_error_detail(
                    "validation_error",
                    "Invalid request.",
                    fields,
                )
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        settings = _get_app_settings(request)
        logger.exception(
            "unhandled_exception",
            extra={
                "path": request.url.path,
                "method": request.method,
            },
        )

        message = (
            str(exc)
            if settings.app_env in {AppEnv.DEVELOPMENT, AppEnv.TEST}
            else "An unexpected error occurred."
        )

        return JSONResponse(
            status_code=500,
            content={
                "detail": build_error_detail(
                    "internal_server_error",
                    message,
                )
            },
        )


def _format_error_field(location: tuple[Any, ...] | list[Any]) -> str:
    parts = [str(part) for part in location]
    if parts and parts[0] in {"body", "query", "path", "header"}:
        parts = parts[1:]
    return ".".join(parts)


def _get_app_settings(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]
