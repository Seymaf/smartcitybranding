"""Traffic Flow connector (TomTom) for the Tourism component."""
from __future__ import annotations
from typing import Any, Dict, List
from connectors.base import BaseConnector
from core.config import TOMTOM_API_KEY
from core.models import AccessTier, BrandingPillar, CityContext, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence

class TrafficConnector(BaseConnector):
    source_id = "tomtom_traffic_flow"
    name = "TomTom Traffic Flow"
    component = SmartCityComponent.TOURISM
    pillar = BrandingPillar.IMAGE
    measurement_track = "Mobility & Traffic Infrastructure"
    cadence = UpdateCadence.INTRA_HOUR
    is_realtime = True

    def fetch(self, city: CityContext) -> RawObservation:
        if not TOMTOM_API_KEY:
            return RawObservation(
                source_id=self.source_id,
                component=self.component,
                available=True,
                data={"current_speed_kmh": 36, "free_flow_speed_kmh": 45, "congestion_ratio": 0.20, "simulated": True},
                metadata={"source": "baseline_estimator"},
            )
        url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
        try:
            payload = self.http_get_json(url, params={"point": f"{city.latitude},{city.longitude}", "key": TOMTOM_API_KEY})
            segment = payload["flowSegmentData"]
            current_speed = segment.get("currentSpeed", 35)
            free_flow = segment.get("freeFlowSpeed", 45)
            congestion = round(1 - (current_speed / free_flow), 2) if current_speed and free_flow else 0.15
            return RawObservation(
                source_id=self.source_id,
                component=self.component,
                available=True,
                data={"current_speed_kmh": current_speed, "free_flow_speed_kmh": free_flow, "congestion_ratio": congestion, "simulated": False},
            )
        except Exception as exc:
            return self.fallback(city, exc)

    def normalize(self, observation: RawObservation) -> List[NormalizedMetric]:
        data = observation.data
        if not observation.available or not data:
            return [NormalizedMetric(name="mobility_fluidity", display_name="Traffic Fluidity", raw_value="Unavailable", unit="score", score=50.0, status_label="No Data")]
        congestion = data.get("congestion_ratio", 0.2)
        current_speed = data.get("current_speed_kmh", 35)
        fluidity = max(0.0, min(100.0, (1.0 - congestion) * 100.0))
        status = "Fluid" if congestion < 0.2 else ("Moderate" if congestion < 0.45 else "Congested")
        return [NormalizedMetric(name="mobility_fluidity", display_name="Traffic Fluidity", raw_value=f"{current_speed} km/h", unit="speed", score=round(fluidity, 1), status_label=status)]
