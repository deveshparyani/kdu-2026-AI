import os
from typing import Any, Literal

import requests
from langchain.tools import tool
from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings


class WeatherInput(BaseModel):
    """Input for weather queries."""
    location: str = Field(description="The location to get the weather for")
    units: Literal["celsius", "fahrenheit"] = Field(
        default="celsius",
        description="Units of temperature"
    )
    include_forecast: bool = Field(
        default=False,
        description="Whether to include a short forecast"
    )

    @field_validator("include_forecast", mode="before")
    @classmethod
    def parse_include_forecast(cls, value):
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "yes", "1"}:
                return True
            if lowered in {"false", "no", "0"}:
                return False

        return value


@tool(args_schema=WeatherInput)
def get_weather(
    location: str,
    units: Literal["celsius", "fahrenheit"] = "celsius",
    include_forecast: bool = False,
) -> dict[str, Any]:
    """Get current weather for a location, with optional forecast."""

    settings = get_settings()
    api_key = settings.openweathermap_api_key

    if not api_key:
        raise ValueError("OPENWEATHERMAP_API_KEY is not set")

    unit_map = {
        "celsius": "metric",
        "fahrenheit": "imperial",
    }
    unit_value = unit_map[units]

    geo_url = "https://api.openweathermap.org/geo/1.0/direct"
    geo_response = requests.get(
        geo_url,
        params={"q": location, "limit": 1, "appid": api_key},
        timeout=10,
    )
    geo_response.raise_for_status()
    geo_data = geo_response.json()

    if not geo_data:
        raise ValueError(f"Location '{location}' not found")

    lat = geo_data[0]["lat"]
    lon = geo_data[0]["lon"]
    city_name = geo_data[0]["name"]

    weather_url = "https://api.openweathermap.org/data/2.5/weather"
    weather_response = requests.get(
        weather_url,
        params={"lat": lat, "lon": lon, "appid": api_key, "units": unit_value},
        timeout=10,
    )
    weather_response.raise_for_status()
    weather_data = weather_response.json()

    result = {
        "location": city_name,
        "temperature": weather_data["main"]["temp"],
        "units": units,
        "summary": weather_data["weather"][0]["description"],
        "forecast": [],
    }

    if include_forecast:
        forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
        forecast_response = requests.get(
            forecast_url,
            params={"lat": lat, "lon": lon, "appid": api_key, "units": unit_value},
            timeout=10,
        )
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()

        result["forecast"] = [
            {
                "time": item["dt_txt"],
                "temp": item["main"]["temp"],
                "description": item["weather"][0]["description"],
            }
            for item in forecast_data["list"][:5]
        ]

    return result
