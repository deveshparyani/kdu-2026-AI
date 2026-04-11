import os
import sys
from typing import Literal, Optional
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
from pydantic import BaseModel
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent

from app.tools.weather import get_weather

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    raise ValueError("GROQ_API_KEY is not set")


class WeatherData(BaseModel):
    location: Optional[str] = None
    temperature: Optional[float] = None
    units: Optional[str] = None
    summary: Optional[str] = None


class AssistantResponse(BaseModel):
    request_type: Literal["weather", "general"]
    answer: Optional[str] = None
    weather: Optional[WeatherData] = None


model = init_chat_model("groq:llama-3.1-8b-instant")

agent = create_agent(
    model=model,
    tools=[get_weather],
    system_prompt=(
        "You are a helpful assistant. "
        "Use the weather tool whenever the user asks about weather. "
        "Do not make up weather data."
    ),
    response_format=AssistantResponse,
)


def ensure_weather_response(response: AssistantResponse) -> AssistantResponse:
    if response.request_type != "weather":
        return response

    weather = response.weather
    if not weather or not weather.location:
        raise ValueError("Weather request did not include a location")

    if weather.temperature is not None and weather.units is not None:
        return response

    weather_result = get_weather.invoke({
        "location": weather.location,
        "units": weather.units or "celsius",
        "include_forecast": False,
    })

    return AssistantResponse(
        request_type="weather",
        answer=response.answer,
        weather=WeatherData(
            location=weather_result["location"],
            temperature=weather_result["temperature"],
            units=weather_result["units"],
            summary=weather_result.get("summary"),
        ),
    )


def main() -> None:
    result = agent.invoke({
        "messages": [
            {"role": "user", "content": "What's the weather in Bangalore?"}
        ]
    })
    result["structured_response"] = ensure_weather_response(
        result["structured_response"]
    )

    print(result)
    print(result.get("structured_response"))


if __name__ == "__main__":
    main()
