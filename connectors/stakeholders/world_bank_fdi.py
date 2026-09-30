"""World Bank FDI net inflows (% of GDP) — national investment-climate proxy."""
from __future__ import annotations

from typing import List

from connectors.base import BaseConnector, linear
from connectors.world_bank import latest_value
from core.models import CityContext, GeoLevel, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence

WDI_SOURCE = 2
FDI_CODE = "BX.KLT.DINV.WD.GD.ZS"


class WorldBankFDIConnector(BaseConnector):
    source_id = "world_bank_fdi"
    name = "World Bank FDI net inflows"
    component = SmartCityComponent.STAKEHOLDERS
    measurement_track = "Investment & Capital Flows"
    link = "https://data.worldbank.org/indicator/BX.KLT.DINV.WD.GD.ZS"
    cadence = UpdateCadence.PERIODIC_BENCHMARK
    geo_level = GeoLevel.NATIONAL_PROXY

    def fetch(self, city: CityContext) -> RawObservation:
        value = latest_value(city.country_iso3, (FDI_CODE,), WDI_SOURCE)
        if not value:
            return self.no_data(f"no FDI value returned for {city.country_iso3}")
        return self.ok({"country": city.country_iso3, "fdi_pct_gdp": value.value, "year": value.year})

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        d = observation.data
        return [self.metric(
            "fdi_inflows", f"FDI net inflows ({d['country']}, {d['year']})", f"{d['fdi_pct_gdp']:.2f}% of GDP", "% GDP",
            linear(d["fdi_pct_gdp"], -1, 5),
            note="Scaled -1% (net outflow) to 5% of GDP; national figure, not city-specific.",
        )]
