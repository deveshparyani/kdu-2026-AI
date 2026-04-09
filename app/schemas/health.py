from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.core.config import AppEnv


class HealthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "service": "fastapi-template",
                "environment": "production",
                "version": "0.1.0",
            }
        }
    )

    status: Literal["ok"]
    service: str
    environment: AppEnv
    version: str


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ready",
                "service": "fastapi-template",
                "environment": "production",
                "version": "0.1.0",
                "database": "ok",
            }
        }
    )

    status: Literal["ready"]
    service: str
    environment: AppEnv
    version: str
    database: Literal["ok"]
