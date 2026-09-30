"""AQICN / World Air Quality Index: nearest station's real-time AQI."""
from __future__ import annotations

from typing import List

from connectors.base import BaseConnector, linear
from core.config import credential
from core.models import CityContext, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence

FEED_URL = "https://api.waqi.info/feed/geo:{lat};{lon}/"


class AQICNConnector(BaseConnector):
    source_id = "aqicn"
    name = "AQICN / World Air Quality Index"
    component = SmartCityComponent.SUSTAINABILITY
    measurement_track = "Air Quality"
    link = "https://aqicn.org/api/"
    cadence = UpdateCadence.INTRA_HOUR
    required_credentials = ("AQICN_TOKEN",)

    def fetch(self, city: CityContext) -> RawObservation:
        payload = self.get_json(FEED_URL.format(lat=city.latitude, lon=city.longitude), {"token": credential("AQICN_TOKEN")})
        if payload.get("status") != "ok":
            raise ValueError(f"AQICN status {payload.get('status')}: {payload.get('data')}")
        data = payload["data"]
        if not isinstance(data.get("aqi"), (int, float)):
            return self.no_data("nearest station reports no current AQI")
        return self.ok({
            "aqi": data["aqi"],
            "station": (data.get("city") or {}).get("name"),
            "dominant_pollutant": data.get("dominentpol"),
            "measured_at": (data.get("time") or {}).get("iso"),
        })

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        d = observation.data
        return [self.metric("aqicn_aqi", "Air quality index (nearest station)", d["aqi"], "US AQI",
                            linear(d["aqi"], 200, 0), note=f"Station: {d['station']}. US EPA scale, 0-50 good.")]
