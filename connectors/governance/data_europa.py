"""data.europa.eu search API: city datasets harvested into the EU open-data portal."""
from __future__ import annotations

from typing import List

from connectors.base import BaseConnector, log_scale
from core.models import CityContext, NormalizedMetric, RawObservation, SmartCityComponent, ValueDimension

SEARCH_URL = "https://data.europa.eu/api/hub/search/search"


class DataEuropaConnector(BaseConnector):
    source_id = "data_europa_eu"
    name = "data.europa.eu API"
    component = SmartCityComponent.E_GOVERNANCE
    measurement_track = "Open Data & Transparency"
    link = "https://dataeuropa.gitlab.io/data-provider-manual/api-documentation/"

    def fetch(self, city: CityContext) -> RawObservation:
        payload = self.get_json(SEARCH_URL, {"q": city.data_europa_query, "filter": "dataset", "limit": 0})
        count = int(payload["result"]["count"])
        if count == 0:
            return self.no_data(f"no datasets matched {city.data_europa_query!r}")
        return self.ok({"datasets": count, "query": city.data_europa_query})

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        count = observation.data["datasets"]
        return [self.metric(
            "eu_open_datasets", "Datasets on data.europa.eu", count, "datasets",
            log_scale(count, 10, 20000), values=(ValueDimension.PARTICIPATORY,),
            note="Keyword match; may include datasets that only mention the city.",
        )]
