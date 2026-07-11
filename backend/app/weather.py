from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from urllib.parse import urlencode

from app.models import WeatherSnapshot
from app.data_sources import _get_json


GEOCODE_BASE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_BASE_URL = "https://api.open-meteo.com/v1/forecast"


def weather_for_location(location: str, game_date: str, venue_name: str | None = None) -> WeatherSnapshot | None:
    coordinates = _geocode(location)
    if coordinates is None:
        return None

    latitude, longitude, resolved_name = coordinates
    forecast = _forecast(latitude, longitude)
    if not isinstance(forecast, dict):
        return None

    hourly = forecast.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return None

    target = _target_hour(game_date)
    index = min(range(len(times)), key=lambda item: abs(_parse_hour(times[item]) - target))
    temperature = _at(hourly.get("temperature_2m"), index)
    wind = _at(hourly.get("wind_speed_10m"), index)
    gust = _at(hourly.get("wind_gusts_10m"), index)
    precipitation = _at(hourly.get("precipitation_probability"), index)
    return WeatherSnapshot(
        venue_name=venue_name,
        location_name=resolved_name,
        temperature_f=temperature,
        wind_mph=wind,
        wind_gust_mph=gust,
        precipitation_probability=precipitation,
        summary=_summary(temperature, wind, gust, precipitation),
    )


@lru_cache(maxsize=128)
def _geocode(location: str) -> tuple[float, float, str] | None:
    payload = _get_json(f"{GEOCODE_BASE_URL}?{urlencode({'name': location, 'count': 1, 'language': 'en', 'format': 'json'})}")
    results = payload.get("results") if isinstance(payload, dict) else None
    if not results:
        return None
    result = results[0]
    name = ", ".join(part for part in [result.get("name"), result.get("admin1"), result.get("country_code")] if part)
    return float(result["latitude"]), float(result["longitude"]), name


@lru_cache(maxsize=128)
def _forecast(latitude: float, longitude: float) -> dict:
    params = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,precipitation_probability,wind_speed_10m,wind_gusts_10m",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "forecast_days": 16,
            "timezone": "auto",
        }
    )
    payload = _get_json(f"{FORECAST_BASE_URL}?{params}")
    return payload if isinstance(payload, dict) else {}


def _target_hour(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _parse_hour(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _at(values: list | None, index: int) -> float | None:
    if values is None or index >= len(values):
        return None
    value = values[index]
    return round(float(value), 1) if value is not None else None


def _summary(temperature: float | None, wind: float | None, gust: float | None, precipitation: float | None) -> str:
    parts = []
    if temperature is not None:
        parts.append(f"{temperature:.0f}F")
    if wind is not None:
        parts.append(f"{wind:.0f} mph wind")
    if gust is not None and gust >= 25:
        parts.append(f"{gust:.0f} mph gusts")
    if precipitation is not None:
        parts.append(f"{precipitation:.0f}% precip")
    return ", ".join(parts) if parts else "Weather unavailable"
