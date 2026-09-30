"""OpenAQ v3: latest readings from official and low-cost sensors near the city."""
from __future__ import annotations

from statistics import mean
from typing import Dict, List

from connectors.base import BaseConnector, linear
from core.config import credential
from core.models import CityContext, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence

API = "https://api.openaq.org/v3"
RADIUS_M = 12000
MAX_LOCATIONS = 5
PARAMETERS = {"pm25", "no2"}


class OpenAQConnector(BaseConnector):
    source_id = "openaq"
    name = "OpenAQ API"
    component = SmartCityComponent.SUSTAINABILITY
    measurement_track = "Air Quality"
    link = "https://docs.openaq.org/about/about"
    cadence = UpdateCadence.INTRA_HOUR
    required_credentials = ("OPENAQ_API_KEY",)

    def fetch(self, city: CityContext) -> RawObservation:
        headers = {"X-API-Key": credential("OPENAQ_API_KEY")}
        locations = self.get_json(f"{API}/locations", {
            "coordinates": f"{city.latitude},{city.longitude}", "radius": RADIUS_M, "limit": 50,
        }, headers=headers).get("results", [])

        # Map sensor id -> parameter name for the parameters we score.
        sensor_param: Dict[int, str] = {}
        chosen = []
        for loc in locations:
            relevant = {s["id"]: s["parameter"]["name"] for s in loc.get("sensors", []) if s.get("parameter", {}).get("name") in PARAMETERS}
            if relevant:
                sensor_param.update(relevant)
                chosen.append(loc)
            if len(chosen) >= MAX_LOCATIONS:
                break
        if not chosen:
            return self.no_data(f"no PM2.5/NO2 sensors within {RADIUS_M // 1000} km")

        readings: Dict[str, List[float]] = {p: [] for p in PARAMETERS}
        for loc in chosen:
            for row in self.get_json(f"{API}/locations/{loc['id']}/latest", headers=headers).get("results", []):
                param = sensor_param.get(row.get("sensorsId"))
                if param and row.get("value") is not None and row["value"] >= 0:
                    readings[param].append(float(row["value"]))
        averages = {p: round(mean(v), 1) for p, v in readings.items() if v}
        if not averages:
            return self.no_data("sensors found but no current readings")
        return self.ok({"stations": [loc.get("name") for loc in chosen], **averages})

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        d = observation.data
        stations = f"{len(d['stations'])} stations"
        metrics = []
        if "pm25" in d:
            metrics.append(self.metric("openaq_pm25", "PM2.5 (sensor average)", d["pm25"], "µg/m³",
                                       linear(d["pm25"], 50, 5), note=stations))
        if "no2" in d:
            metrics.append(self.metric("openaq_no2", "NO2 (sensor average)", d["no2"], "µg/m³",
                                       linear(d["no2"], 100, 10), note=f"{stations}; 10 µg/m³ = WHO annual guideline."))
        return metrics
