"""World Bank Worldwide Governance Indicators — institutional quality.

National-level proxy: WGI is published per country, so every metric is
flagged `national_proxy` and down-weighted by the scoring engine.
"""
from __future__ import annotations

from typing import List

from connectors.base import BaseConnector, linear
from connectors.world_bank import latest_value
from core.models import CityContext, GeoLevel, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence, ValueDimension

WGI_SOURCE = 3

# (metric name, display name, candidate codes, value dimensions)
INDICATORS = [
    ("wgi_voice_accountability", "Voice & accountability", ("VA.EST", "GOV_WGI_VA.EST"), (ValueDimension.DEMOCRATIC, ValueDimension.PARTICIPATORY)),
    ("wgi_rule_of_law", "Rule of law", ("RL.EST", "GOV_WGI_RL.EST"), (ValueDimension.DEMOCRATIC,)),
    ("wgi_control_of_corruption", "Control of corruption", ("CC.EST", "GOV_WGI_CC.EST"), (ValueDimension.DEMOCRATIC,)),
    ("wgi_government_effectiveness", "Government effectiveness", ("GE.EST", "GOV_WGI_GE.EST"), ()),
]


class WorldBankGovernanceConnector(BaseConnector):
    source_id = "world_bank_wgi"
    name = "World Bank Worldwide Governance Indicators"
    component = SmartCityComponent.E_GOVERNANCE
    measurement_track = "Institutional Quality"
    link = "https://databank.worldbank.org/source/worldwide-governance-indicators"
    cadence = UpdateCadence.PERIODIC_BENCHMARK
    geo_level = GeoLevel.NATIONAL_PROXY

    def fetch(self, city: CityContext) -> RawObservation:
        found = {}
        for name, _display, codes, _values in INDICATORS:
            value = latest_value(city.country_iso3, codes, WGI_SOURCE)
            if value:
                found[name] = {"estimate": value.value, "year": value.year, "code": value.code}
        if not found:
            return self.no_data(f"no WGI values returned for {city.country_iso3}")
        return self.ok({"country": city.country_iso3, "indicators": found})

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        indicators = observation.data["indicators"]
        metrics = []
        for name, display, _codes, values in INDICATORS:
            item = indicators.get(name)
            if not item:
                continue
            metrics.append(self.metric(
                name, f"{display} ({city.country_iso3}, {item['year']})", f"{item['estimate']:+.2f}", "WGI estimate",
                linear(item["estimate"], -2.5, 2.5), values=values,
                note="WGI estimates run -2.5 (weak) to +2.5 (strong).",
            ))
        return metrics
