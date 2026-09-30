"""GDELT 2.0 DOC API: global news volume and tone about the city (no key)."""
from __future__ import annotations

from statistics import mean
from typing import List

from connectors.base import BaseConnector, linear, log_scale
from core.models import CityContext, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence

DOC_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
TIMESPAN = "7d"


def _series_values(payload: dict) -> List[float]:
    timeline = payload.get("timeline") or []
    if not timeline:
        return []
    return [float(point["value"]) for point in timeline[0].get("data", []) if point.get("value") is not None]


class GDELTNewsConnector(BaseConnector):
    source_id = "gdelt_doc_api"
    name = "GDELT 2.0 DOC API"
    component = SmartCityComponent.SMART_COMMUNICATION
    measurement_track = "Public Perception"
    link = "https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/"
    cadence = UpdateCadence.INTRA_HOUR

    def fetch(self, city: CityContext) -> RawObservation:
        base = {"query": city.news_query, "format": "json", "timespan": TIMESPAN}
        volume = _series_values(self.get_json(DOC_API_URL, {**base, "mode": "timelinevolraw"}))
        tone = _series_values(self.get_json(DOC_API_URL, {**base, "mode": "timelinetone"}))
        if not volume:
            return self.no_data(f"no articles matched {city.news_query!r} in the last {TIMESPAN}")
        return self.ok({
            "articles": int(sum(volume)),
            "average_tone": round(mean(tone), 2) if tone else None,
            "timespan": TIMESPAN,
            "query": city.news_query,
        })

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        data = observation.data
        metrics = [
            self.metric("news_volume", "Global news attention", f"{data['articles']} articles / {TIMESPAN}", "articles",
                        log_scale(data["articles"], 10, 5000)),
        ]
        if data.get("average_tone") is not None:
            metrics.append(self.metric(
                "news_tone", "Global news tone", f"{data['average_tone']:+.2f}", "GDELT tone",
                linear(data["average_tone"], -5, 5),
                note="GDELT tone runs roughly -10..+10; -5..+5 covers almost all city coverage.",
            ))
        return metrics
