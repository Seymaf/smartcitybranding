"""PeeringDB: data centres and internet exchange points located in the city (no key)."""
from __future__ import annotations

from typing import List

from connectors.base import BaseConnector, linear, log_scale
from core.models import CityContext, NormalizedMetric, RawObservation, SmartCityComponent, ValueDimension

API_URL = "https://www.peeringdb.com/api/{kind}"


class PeeringDBConnector(BaseConnector):
    source_id = "peeringdb"
    name = "PeeringDB API"
    component = SmartCityComponent.DIGITAL_INFRASTRUCTURE
    measurement_track = "Digital Infrastructure Presence & Investment"
    link = "https://www.peeringdb.com/apidocs/"

    def fetch(self, city: CityContext) -> RawObservation:
        params = {"city": city.name, "country": city.country_code}
        facilities = self.get_json(API_URL.format(kind="fac"), params).get("data", [])
        exchanges = self.get_json(API_URL.format(kind="ix"), params).get("data", [])
        return self.ok({
            "facilities": len(facilities),
            "exchanges": len(exchanges),
            "exchange_names": [ix.get("name") for ix in exchanges],
        })

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        d = observation.data
        return [
            self.metric("data_centres", "Data-centre facilities", d["facilities"], "facilities",
                        log_scale(d["facilities"], 1, 50), values=(ValueDimension.INNOVATIVE,)),
            self.metric("internet_exchanges", "Internet exchange points", d["exchanges"], "IXPs",
                        linear(d["exchanges"], 0, 3), values=(ValueDimension.INNOVATIVE,)),
        ]
