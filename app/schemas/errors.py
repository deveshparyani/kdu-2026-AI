from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ErrorField(BaseModel):
    field: str
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    fields: list[ErrorField] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": {
                    "code": "validation_error",
                    "message": "Invalid request.",
                    "fields": [
                        {
                            "field": "password",
                            "message": "Field required",
                        }
                    ],
                }
            }
        }
    )

    detail: ErrorDetail
