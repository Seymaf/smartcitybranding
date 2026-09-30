"""OpenWeatherMap Air Pollution API: modelled air quality at the city centre."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from connectors.base import BaseConnector, linear
from core.config import credential
from core.models import AccessTier, CityContext, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence

AIR_POLLUTION_URL = "https://api.openweathermap.org/data/2.5/air_pollution"
AQI_LABELS = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}


class OpenWeatherAirConnector(BaseConnector):
    source_id = "openweather_air"
    name = "OpenWeatherMap Air Pollution API"
    component = SmartCityComponent.SUSTAINABILITY
    measurement_track = "Air Quality"
    link = "https://openweathermap.org/api/air-pollution"
    cadence = UpdateCadence.INTRA_HOUR
    access_tier = AccessTier.FREEMIUM
    required_credentials = ("OPENWEATHER_API_KEY",)

    def fetch(self, city: CityContext) -> RawObservation:
        entry = self.get_json(AIR_POLLUTION_URL, {
            "lat": city.latitude, "lon": city.longitude, "appid": credential("OPENWEATHER_API_KEY"),
        })["list"][0]
        c = entry["components"]
        return self.ok({
            "aqi": entry["main"]["aqi"],
            "aqi_label": AQI_LABELS.get(entry["main"]["aqi"], "Unknown"),
            "pm2_5": c.get("pm2_5"), "pm10": c.get("pm10"), "no2": c.get("no2"),
            "o3": c.get("o3"), "so2": c.get("so2"), "co": c.get("co"),
            "measured_at": datetime.fromtimestamp(entry["dt"], tz=timezone.utc).isoformat(),
        })

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        d = observation.data
        metrics = [self.metric("owm_aqi", "Air quality index (OpenWeather)", f"{d['aqi']} – {d['aqi_label']}",
                               "AQI 1-5", linear(d["aqi"], 5, 1))]
        if d.get("pm2_5") is not None:
            metrics.append(self.metric("owm_pm25", "PM2.5 (modelled)", d["pm2_5"], "µg/m³", linear(d["pm2_5"], 50, 5),
                                       note="5 µg/m³ = WHO annual guideline -> 100; 50 µg/m³ -> 0."))
        return metrics
