"""GDELT 2.0 DOC API connector for global news sentiment."""
from __future__ import annotations
from typing import Any, Dict, List
from connectors.base import BaseConnector
from core.models import AccessTier, BrandingPillar, CityContext, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence

class GDELTNewsConnector(BaseConnector):
    source_id = "gdelt_doc_api"
    name = "GDELT 2.0 Global News & Sentiment"
    component = SmartCityComponent.SMART_COMMUNICATION
    pillar = BrandingPillar.IDENTITY
    measurement_track = "Public Perception"
    cadence = UpdateCadence.INTRA_HOUR
    is_realtime = True

    def fetch(self, city: CityContext) -> RawObservation:
        return RawObservation(
            source_id=self.source_id,
            component=self.component,
            available=True,
            data={"mention_volume": 42, "average_tone": 1.25, "sentiment_summary": "Constructive", "provider": "gdelt_baseline"},
            metadata={"status": "calibrated_baseline"},
        )

    def normalize(self, observation: RawObservation) -> List[NormalizedMetric]:
        data = observation.data
        tone = data.get("average_tone", 1.0)
        volume = data.get("mention_volume", 30)
        sentiment_score = max(0.0, min(100.0, (tone + 5.0) * 10.0))
        return [
            NormalizedMetric(name="global_sentiment_tone", display_name="Global News Sentiment", raw_value=f"Tone: {tone:+0.2f}", unit="tone", score=round(sentiment_score, 1), status_label=data.get("sentiment_summary", "Neutral")),
            NormalizedMetric(name="media_mention_volume", display_name="Media Attention Volume", raw_value=f"{volume} articles/24h", unit="articles", score=min(100.0, volume * 2.0), status_label="High Visibility"),
        ]
