"""OpenCelliD: crowdsourced cell-tower density around the city centre."""
from __future__ import annotations

import math
from typing import List

from connectors.base import BaseConnector, log_scale
from core.config import credential
from core.models import CityContext, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence

AREA_SIZE_URL = "https://opencellid.org/cell/getInAreaSize"
HALF_SIDE_KM = 1.0  # 2 km x 2 km box — the API's maximum query area is small


def bbox(lat: float, lon: float, half_side_km: float = HALF_SIDE_KM) -> str:
    dlat = half_side_km / 111.32
    dlon = half_side_km / (111.32 * math.cos(math.radians(lat)))
    return f"{lat - dlat:.5f},{lon - dlon:.5f},{lat + dlat:.5f},{lon + dlon:.5f}"


class OpenCelliDConnector(BaseConnector):
    source_id = "opencellid"
    name = "OpenCelliD"
    component = SmartCityComponent.DIGITAL_INFRASTRUCTURE
    measurement_track = "Network-Level Signal"
    link = "https://wiki.opencellid.org/wiki/API"
    cadence = UpdateCadence.PERIODIC_BENCHMARK
    required_credentials = ("OPENCELLID_API_KEY",)

    def fetch(self, city: CityContext) -> RawObservation:
        payload = self.get_json(AREA_SIZE_URL, {
            "key": credential("OPENCELLID_API_KEY"),
            "BBOX": bbox(city.latitude, city.longitude),
            "format": "json",
        })
        if "count" not in payload:
            raise ValueError(payload.get("error") or "unexpected OpenCelliD response")
        return self.ok({"cells_in_4km2": int(payload["count"])})

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        cells = observation.data["cells_in_4km2"]
        return [self.metric("cell_density", "Mobile cells in central 4 km²", cells, "cells",
                            log_scale(cells, 10, 2000), note="Crowdsourced; coverage varies by contributor activity.")]
