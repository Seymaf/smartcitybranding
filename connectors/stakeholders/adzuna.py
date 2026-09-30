"""Adzuna API: labour-market demand and the share of tech jobs in the city."""
from __future__ import annotations

from typing import List

from connectors.base import BaseConnector, linear, log_scale
from core.config import credential
from core.models import AccessTier, CityContext, NormalizedMetric, RawObservation, SmartCityComponent, ValueDimension

SEARCH_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"


class AdzunaConnector(BaseConnector):
    source_id = "adzuna_jobs"
    name = "Adzuna Jobs API"
    component = SmartCityComponent.STAKEHOLDERS
    measurement_track = "Labor Market & Talent Demand"
    link = "https://developer.adzuna.com/"
    access_tier = AccessTier.FREEMIUM
    required_credentials = ("ADZUNA_APP_ID", "ADZUNA_APP_KEY")

    def _search(self, city: CityContext, **extra) -> dict:
        return self.get_json(
            SEARCH_URL.format(country=city.adzuna_country),
            {
                "app_id": credential("ADZUNA_APP_ID"),
                "app_key": credential("ADZUNA_APP_KEY"),
                "where": city.name,
                "results_per_page": 1,
                "content-type": "application/json",
                **extra,
            },
        )

    def fetch(self, city: CityContext) -> RawObservation:
        total = self._search(city)
        count = int(total.get("count") or 0)
        if count == 0:
            return self.no_data(f"no job ads found for {city.name}")
        tech = int(self._search(city, category="it-jobs").get("count") or 0)
        return self.ok({"job_ads": count, "tech_job_ads": tech, "mean_salary": total.get("mean")})

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        d = observation.data
        tech_share = d["tech_job_ads"] / d["job_ads"]
        return [
            self.metric("job_demand", "Open job ads", d["job_ads"], "ads", log_scale(d["job_ads"], 500, 100000)),
            self.metric("tech_job_share", "Share of IT job ads", f"{tech_share:.1%}", "share",
                        linear(tech_share, 0.02, 0.15), values=(ValueDimension.INNOVATIVE,),
                        note="2% -> 0, 15% -> 100."),
        ]
