"""Open311 GeoReport v2: citizen service requests and how the city responds.

Only runs when the city publishes an Open311 endpoint (set
`CityContext.open311_url`). Bremen does not currently publish one.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import median
from typing import List, Optional

from connectors.base import BaseConnector, linear, log_scale
from core.models import CityContext, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence, ValueDimension

WINDOW_DAYS = 30


def _parse(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


class Open311Connector(BaseConnector):
    source_id = "open311_georeport"
    name = "Open311 GeoReport v2"
    component = SmartCityComponent.SMART_COMMUNICATION
    measurement_track = "Citizen <-> Machine Interaction"
    link = "https://www.open311.org/"
    cadence = UpdateCadence.INTRA_HOUR

    def missing_configuration(self, city: CityContext) -> Optional[str]:
        return None if city.open311_url else f"{city.name} has no Open311 endpoint configured"

    def fetch(self, city: CityContext) -> RawObservation:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=WINDOW_DAYS)
        requests_ = self.get_json(
            f"{city.open311_url.rstrip('/')}/requests.json",
            {
                "start_date": start.isoformat(timespec="seconds"),
                "end_date": end.isoformat(timespec="seconds"),
                "jurisdiction_id": city.open311_jurisdiction_id,
            },
        )
        if not requests_:
            return self.no_data(f"no service requests in the last {WINDOW_DAYS} days")
        closed = [r for r in requests_ if str(r.get("status", "")).lower() == "closed"]
        durations = []
        for r in closed:
            opened, updated = _parse(r.get("requested_datetime")), _parse(r.get("updated_datetime"))
            if opened and updated and updated >= opened:
                durations.append((updated - opened).total_seconds() / 86400)
        return self.ok({
            "requests": len(requests_),
            "closed": len(closed),
            "closed_share": round(len(closed) / len(requests_), 3),
            "median_days_to_close": round(median(durations), 1) if durations else None,
            "window_days": WINDOW_DAYS,
        })

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        d = observation.data
        metrics = [
            self.metric("open311_volume", "Citizen service requests", f"{d['requests']} / {WINDOW_DAYS}d", "requests",
                        log_scale(d["requests"], 10, 10000), values=(ValueDimension.PARTICIPATORY,)),
            self.metric("open311_resolution", "Service requests resolved", f"{d['closed_share']:.0%}", "share",
                        d["closed_share"] * 100, values=(ValueDimension.PARTICIPATORY,)),
        ]
        if d.get("median_days_to_close") is not None:
            metrics.append(self.metric("open311_speed", "Median days to resolve", d["median_days_to_close"], "days",
                                       linear(d["median_days_to_close"], 30, 1)))
        return metrics
