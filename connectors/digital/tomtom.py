"""TomTom Traffic Flow: live congestion in the city centre."""
from __future__ import annotations

from typing import List

from connectors.base import BaseConnector
from core.config import credential
from core.models import AccessTier, CityContext, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence

FLOW_SEGMENT_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"


class TomTomTrafficConnector(BaseConnector):
    source_id = "tomtom_traffic_flow"
    name = "TomTom Traffic API"
    component = SmartCityComponent.DIGITAL_INFRASTRUCTURE
    measurement_track = "Mobility & Traffic Infrastructure"
    link = "https://developer.tomtom.com/traffic-api/documentation/traffic-flow/flow-segment-data"
    cadence = UpdateCadence.INTRA_HOUR
    access_tier = AccessTier.FREEMIUM
    required_credentials = ("TOMTOM_API_KEY",)

    def fetch(self, city: CityContext) -> RawObservation:
        segment = self.get_json(FLOW_SEGMENT_URL, {
            "point": f"{city.latitude},{city.longitude}",
            "key": credential("TOMTOM_API_KEY"),
        })["flowSegmentData"]
        current, free_flow = segment.get("currentSpeed"), segment.get("freeFlowSpeed")
        if not current or not free_flow:
            return self.no_data("TomTom returned no speed values for the city-centre segment")
        return self.ok({
            "current_speed_kmh": current,
            "free_flow_speed_kmh": free_flow,
            "congestion_ratio": round(max(0.0, 1 - current / free_flow), 2),
            "road_closure": segment.get("roadClosure", False),
            "confidence": segment.get("confidence"),
        })

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        d = observation.data
        return [self.metric(
            "traffic_fluidity", "City-centre traffic fluidity",
            f"{d['current_speed_kmh']} of {d['free_flow_speed_kmh']} km/h", "km/h",
            (1 - d["congestion_ratio"]) * 100,
            note="Single city-centre road segment; a snapshot, not a city-wide average.",
        )]
