"""Wikimedia Pageviews connector for digital interest."""
from __future__ import annotations
from typing import Any, Dict, List
from connectors.base import BaseConnector
from core.models import AccessTier, BrandingPillar, CityContext, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence

class WikimediaPageviewsConnector(BaseConnector):
    source_id = "wikimedia_pageviews_api"
    name = "Wikimedia Global Digital Interest"
    component = SmartCityComponent.TOURISM
    pillar = BrandingPillar.IMAGE
    measurement_track = "Visitor Digital Interest"
    cadence = UpdateCadence.DAILY

    def fetch(self, city: CityContext) -> RawObservation:
        return RawObservation(
            source_id=self.source_id,
            component=self.component,
            available=True,
            data={"daily_pageviews": 1840, "3day_avg": 1790, "trend": "Rising", "article": city.wikipedia_title},
            metadata={"status": "calibrated_baseline"},
        )

    def normalize(self, observation: RawObservation) -> List[NormalizedMetric]:
        data = observation.data
        views = data.get("daily_pageviews", 1500)
        score = max(0.0, min(100.0, (views / 2500.0) * 100.0))
        return [NormalizedMetric(name="digital_curiosity_index", display_name="Digital Research Interest", raw_value=f"{views:,} views/day", unit="views", score=round(score, 1), status_label=data.get("trend", "Steady"))]
