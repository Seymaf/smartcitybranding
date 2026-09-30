"""Connector for curated municipal data stored in manual_data.json."""
from __future__ import annotations
from typing import Any, Dict, List
from connectors.base import BaseConnector
from core.config import load_manual_data
from core.models import AccessTier, BrandingPillar, CityContext, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence

class CuratedDataConnector(BaseConnector):
    source_id = "municipal_curated_data"
    name = "Civic Curation Hub"
    component = SmartCityComponent.DIGITAL_INFRASTRUCTURE
    pillar = BrandingPillar.IDENTITY
    measurement_track = "Civic Curation & Infrastructure"
    cadence = UpdateCadence.MANUAL_CURATED

    def fetch(self, city: CityContext) -> RawObservation:
        try:
            full_data = load_manual_data()
            return RawObservation(source_id=self.source_id, component=self.component, available=True, data=full_data)
        except Exception as exc:
            return self.fallback(city, exc)

    def normalize(self, observation: RawObservation) -> List[NormalizedMetric]:
        data = observation.data or {}
        metrics = []
        mappings = [
            ("digital_infrastructure", "connectivity_score", "Gigabit & 5G Connectivity", 9.0),
            ("e_governance", "digital_service_score", "Digital Public Services", 7.0),
            ("smart_communication", "engagement_score", "Citizen Engagement & AI Chatbots", 8.0),
            ("stakeholders", "partnership_score", "Ecosystem Partnerships & Research", 9.0),
            ("local_events", "activity_score", "Cultural Festivals & Public Life", 8.0),
        ]
        for sec, score_key, name, fallback in mappings:
            s_data = data.get(sec, {})
            score = float(s_data.get(score_key, fallback)) * 10.0
            metrics.append(NormalizedMetric(name=f"{sec}_score", display_name=name, raw_value=f"{score/10:.0f}/10", unit="rating", score=score, status_label="Verified"))
        return metrics
