import os

import requests
from dotenv import load_dotenv


load_dotenv()


def get_weather(city: str) -> dict:
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return {
            "error": "WEATHER_API_KEY is not configured.",
            "city": city,
        }

    geo_response = requests.get(
        "http://api.openweathermap.org/geo/1.0/direct",
        params={"q": city, "appid": api_key, "limit": 1},
        timeout=15,
    )
    geo_response.raise_for_status()
    geo_results = geo_response.json()

    if not geo_results:
        return {
            "error": f"Could not find coordinates for {city}.",
            "city": city,
        }

    location = geo_results[0]
    weather_response = requests.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={
            "lat": location["lat"],
            "lon": location["lon"],
            "appid": api_key,
            "units": "metric",
        },
        timeout=15,
    )
    weather_response.raise_for_status()
    weather = weather_response.json()

    return {
        "city": weather.get("name", city),
        "country": location.get("country"),
        "temperature_c": weather.get("main", {}).get("temp"),
        "feels_like_c": weather.get("main", {}).get("feels_like"),
        "humidity": weather.get("main", {}).get("humidity"),
        "condition": weather.get("weather", [{}])[0].get("description"),
        "wind_speed_mps": weather.get("wind", {}).get("speed"),
    }
