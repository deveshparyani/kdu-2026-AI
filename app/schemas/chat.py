from typing import Literal

from pydantic import BaseModel, Field


class HiddenContext(BaseModel):
    user_id: str = Field(description="Stable user identifier from the app")
    thread_id: str = Field(description="Conversation identifier")
    stored_location: str | None = Field(
        default=None,
        description="Known user location from profile or long-term memory",
    )
    style: Literal["default", "expert", "child"] = Field(
        default="default",
        description="Requested communication style",
    )


class ChatRequest(BaseModel):
    message: str = Field(description="User message")
    image_url: str | None = Field(
        default=None,
        description="Optional image URL for future multimodal support",
    )
    context: HiddenContext


class WeatherData(BaseModel):
    location: str
    temperature: float
    units: Literal["celsius", "fahrenheit"]
    summary: str


class ImageAnalysis(BaseModel):
    summary: str
    detected_objects: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    request_type: Literal["general", "weather", "image"] = "general"
    input_type: Literal["text", "multimodal"] = "text"
    style_used: Literal["default", "expert", "child"] = "default"
    answer: str = ""
    weather: WeatherData | None = None
    image_analysis: ImageAnalysis | None = None
    used_location_from_profile: bool = False
    used_tool: str | None = None
    remembered_location: str | None = None
    profile_updated: bool = False
    model_used: str = ""
