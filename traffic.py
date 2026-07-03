"""Fetches traffic flow data for Bremen from the TomTom Traffic API."""

from __future__ import annotations

from typing import Any

import requests

from config import BREMEN_LAT, BREMEN_LON, REQUEST_TIMEOUT, TOMTOM_API_KEY

FLOW_SEGMENT_URL = (
    "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
)


def fetch_traffic() -> dict[str, Any]:
    """Fetches current traffic flow data for Bremen city center from TomTom.

    Returns a dict with current vs. free-flow speed, travel time, and a
    derived congestion ratio (0 = no congestion, closer to 1 = heavy congestion).
    """
    response = requests.get(
        FLOW_SEGMENT_URL,
        params={
            "point": f"{BREMEN_LAT},{BREMEN_LON}",
            "key": TOMTOM_API_KEY,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    segment = response.json()["flowSegmentData"]

    current_speed = segment.get("currentSpeed")
    free_flow_speed = segment.get("freeFlowSpeed")
    congestion_ratio = (
        round(1 - (current_speed / free_flow_speed), 2)
        if current_speed and free_flow_speed
        else None
    )

    return {
        "current_speed_kmh": current_speed,
        "free_flow_speed_kmh": free_flow_speed,
        "current_travel_time_s": segment.get("currentTravelTime"),
        "free_flow_travel_time_s": segment.get("freeFlowTravelTime"),
        "congestion_ratio": congestion_ratio,
        "road_closure": segment.get("roadClosure", False),
        "confidence": segment.get("confidence"),
    }
