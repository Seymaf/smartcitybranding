"""Fetches air quality data for Bremen from the OpenWeatherMap Air Pollution API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from config import BREMEN_LAT, BREMEN_LON, OPENWEATHER_API_KEY, REQUEST_TIMEOUT

AQI_LABELS = {
    1: "Good",
    2: "Fair",
    3: "Moderate",
    4: "Poor",
    5: "Very Poor",
}

AIR_POLLUTION_URL = "https://api.openweathermap.org/data/2.5/air_pollution"


def fetch_air_quality() -> dict[str, Any]:
    """Fetches current air quality for Bremen from OpenWeatherMap.

    Returns a dict with the OpenWeatherMap AQI index (1-5), a human-readable
    label, and the underlying pollutant concentrations (µg/m³).
    """
    response = requests.get(
        AIR_POLLUTION_URL,
        params={
            "lat": BREMEN_LAT,
            "lon": BREMEN_LON,
            "appid": OPENWEATHER_API_KEY,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()

    entry = payload["list"][0]
    aqi = entry["main"]["aqi"]
    components = entry["components"]
    measured_at = datetime.fromtimestamp(entry["dt"], tz=timezone.utc)

    return {
        "aqi": aqi,
        "aqi_label": AQI_LABELS.get(aqi, "Unknown"),
        "co": components.get("co"),
        "no2": components.get("no2"),
        "o3": components.get("o3"),
        "so2": components.get("so2"),
        "pm2_5": components.get("pm2_5"),
        "pm10": components.get("pm10"),
        "measured_at": measured_at.isoformat(),
    }
