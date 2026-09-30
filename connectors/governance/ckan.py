"""CKAN Action API: open datasets published about the city, and how fresh they are.

Most EU/German open-data portals (GovData.de included) run CKAN. Point
`CityContext.ckan_api_url` at the city's own portal when it has one.
"""
from __future__ import annotations

from typing import List, Optional

from connectors.base import BaseConnector, log_scale
from core.models import CityContext, NormalizedMetric, RawObservation, SmartCityComponent, ValueDimension

FRESH_WINDOW = "[NOW-365DAYS TO NOW]"


class CKANOpenDataConnector(BaseConnector):
    source_id = "ckan_open_data"
    name = "CKAN Open Data Action API"
    component = SmartCityComponent.E_GOVERNANCE
    measurement_track = "Open Data & Transparency"
    link = "https://docs.ckan.org/en/latest/api/"

    def missing_configuration(self, city: CityContext) -> Optional[str]:
        return None if city.ckan_api_url else f"{city.name} has no CKAN portal configured"

    def _count(self, city: CityContext, fq: Optional[str] = None) -> int:
        payload = self.get_json(
            f"{city.ckan_api_url.rstrip('/')}/package_search",
            {"q": city.ckan_query, "fq": fq, "rows": 0},
        )
        if not payload.get("success"):
            raise ValueError(f"CKAN returned success=false: {payload.get('error')}")
        return int(payload["result"]["count"])

    def fetch(self, city: CityContext) -> RawObservation:
        total = self._count(city)
        if total == 0:
            return self.no_data(f"no datasets matched {city.ckan_query!r}")
        fresh = self._count(city, fq=f"metadata_modified:{FRESH_WINDOW}")
        return self.ok({"portal": city.ckan_api_url, "datasets": total, "updated_last_year": fresh})

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        d = observation.data
        fresh_share = d["updated_last_year"] / d["datasets"]
        return [
            self.metric("open_datasets", "Open datasets published", d["datasets"], "datasets",
                        log_scale(d["datasets"], 10, 10000), values=(ValueDimension.PARTICIPATORY,),
                        source_url=d["portal"]),
            self.metric("open_data_freshness", "Datasets updated in the last year", f"{fresh_share:.0%}", "share",
                        fresh_share * 100, values=(ValueDimension.PARTICIPATORY,), source_url=d["portal"]),
        ]
