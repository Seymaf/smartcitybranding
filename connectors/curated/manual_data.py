"""Hand-curated assessments from manual_data.json.

These are clearly labelled `curated` evidence and weigh half as much as a
live measurement in the scoring engine. Sections with a `note` (provisional
or estimated) are halved again. They never stand in for a missing API: a
component supported only by curated data is flagged as self-assessed.
"""
from __future__ import annotations

from typing import List

from connectors.base import BaseConnector
from core.config import MANUAL_DATA_PATH, load_manual_data
from core.models import (
    CityContext,
    EvidenceType,
    NormalizedMetric,
    RawObservation,
    SmartCityComponent,
    UpdateCadence,
    ValueDimension,
)

# section -> (score field, display name, component, value dimensions)
SECTIONS = {
    "digital_infrastructure": ("connectivity_score", "Connectivity assessment", SmartCityComponent.DIGITAL_INFRASTRUCTURE, (ValueDimension.INNOVATIVE,)),
    "e_governance": ("digital_service_score", "Digital public services assessment", SmartCityComponent.E_GOVERNANCE, (ValueDimension.PARTICIPATORY,)),
    "smart_communication": ("engagement_score", "Citizen engagement assessment", SmartCityComponent.SMART_COMMUNICATION, (ValueDimension.PARTICIPATORY,)),
    "stakeholders": ("partnership_score", "Partnership ecosystem assessment", SmartCityComponent.STAKEHOLDERS, (ValueDimension.INNOVATIVE,)),
    "local_events": ("activity_score", "Cultural & public-life assessment", SmartCityComponent.TOURISM, ()),
}

CURATED_WEIGHT = 0.5


class CuratedDataConnector(BaseConnector):
    source_id = "manual_data"
    name = "Curated municipal assessments (manual_data.json)"
    component = SmartCityComponent.E_GOVERNANCE  # overridden per metric
    measurement_track = "Curated assessment"
    link = "manual_data.json"
    cadence = UpdateCadence.MANUAL_CURATED
    evidence_type = EvidenceType.CURATED

    def fetch(self, city: CityContext) -> RawObservation:
        if not MANUAL_DATA_PATH.exists():
            return self.no_data("manual_data.json not found")
        return self.ok(load_manual_data())

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        metrics = []
        for section, (field, display, component, values) in SECTIONS.items():
            data = observation.data.get(section) or {}
            if data.get(field) is None:
                continue
            provisional = bool(data.get("note"))
            metrics.append(self.metric(
                f"curated_{section}", display, f"{data[field]}/10 (updated {data.get('last_updated', '?')})", "rating",
                float(data[field]) * 10, values=values, component=component,
                weight=CURATED_WEIGHT * (0.5 if provisional else 1.0),
                note=data.get("note", "") or "Curated assessment; see key facts.",
            ))
        return metrics
