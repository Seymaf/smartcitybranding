"""Air Quality connector (OpenWeatherMap & OpenAQ) for the Sustainability component."""
from __future__ import annotations
from typing import Any, Dict, List
from connectors.base import BaseConnector
from core.config import OPENWEATHER_API_KEY
from core.models import AccessTier, BrandingPillar, CityContext, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence

AQI_LABELS = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}

class AirQualityConnector(BaseConnector):
    source_id = "openaq_air_pollution"
    name = "Air Quality Monitor"
    component = SmartCityComponent.SUSTAINABILITY
    pillar = BrandingPillar.POSITIONING
    measurement_track = "Air Quality"
    cadence = UpdateCadence.INTRA_HOUR
    is_realtime = True
    access_tier = AccessTier.FREE_OPEN

    def fetch(self, city: CityContext) -> RawObservation:
        if not OPENWEATHER_API_KEY:
            return RawObservation(
                source_id=self.source_id,
                component=self.component,
                available=True,
                data={"aqi": 1, "aqi_label": "Good", "co": 210.0, "no2": 12.4, "o3": 48.0, "so2": 1.8, "pm2_5": 7.2, "pm10": 14.5, "simulated": True},
                metadata={"source": "baseline_estimator"},
            )
        url = "https://api.openweathermap.org/data/2.5/air_pollution"
        try:
            payload = self.http_get_json(url, params={"lat": city.latitude, "lon": city.longitude, "appid": OPENWEATHER_API_KEY})
            entry = payload["list"][0]
            aqi = entry["main"]["aqi"]
            comp = entry["components"]
            return RawObservation(
                source_id=self.source_id,
                component=self.component,
                available=True,
                data={"aqi": aqi, "aqi_label": AQI_LABELS.get(aqi, "Unknown"), "pm2_5": comp.get("pm2_5"), "pm10": comp.get("pm10"), "simulated": False},
            )
        except Exception as exc:
            return self.fallback(city, exc)

    def normalize(self, observation: RawObservation) -> List[NormalizedMetric]:
        data = observation.data
        if not observation.available or not data:
            return [NormalizedMetric(name="clean_air_score", display_name="Clean Air Index", raw_value="Unavailable", unit="score", score=50.0, status_label="No Data")]
        aqi = data.get("aqi", 2)
        pm2_5 = data.get("pm2_5", 15.0) or 15.0
        aqi_score = max(0.0, min(100.0, 120.0 - (aqi * 20.0)))
        pm25_score = max(0.0, min(100.0, 100.0 - (pm2_5 * 2.5)))
        combined = round(0.6 * aqi_score + 0.4 * pm25_score, 1)
        return [
            NormalizedMetric(name="clean_air_score", display_name="Clean Air Index", raw_value=data.get("aqi_label", "Moderate"), unit="AQI", score=combined, status_label=data.get("aqi_label", "Moderate")),
            NormalizedMetric(name="pm2_5_concentration", display_name="PM2.5 Particles", raw_value=pm2_5, unit="µg/m³", score=round(pm25_score, 1), status_label="Low" if pm2_5 < 15 else "Elevated"),
        ]
