"""Decidim GraphQL API: participatory-democracy activity on the city's instance.

Decidim (Barcelona, Helsinki and 400+ institutions) exposes a public
GraphQL endpoint at `<instance>/api`. Runs only when the city has an
instance configured in `CityContext.decidim_api_url`.
"""
from __future__ import annotations

from typing import List, Optional

from connectors.base import BaseConnector, log_scale
from core.models import AccessTier, CityContext, NormalizedMetric, RawObservation, SmartCityComponent, ValueDimension

PROCESSES_QUERY = "{ participatoryProcesses { id } }"
METRICS_QUERY = '{ metrics(names: ["participants", "proposals"]) { name count } }'


class DecidimConnector(BaseConnector):
    source_id = "decidim_graphql"
    name = "Decidim participatory platform"
    component = SmartCityComponent.E_GOVERNANCE
    measurement_track = "Digital Participation & Civic Tech"
    link = "https://docs.decidim.org/en/develop/understand/about.html"
    access_tier = AccessTier.SELF_HOSTED

    def missing_configuration(self, city: CityContext) -> Optional[str]:
        return None if city.decidim_api_url else f"{city.name} has no Decidim instance configured"

    def fetch(self, city: CityContext) -> RawObservation:
        processes = self.post_json(city.decidim_api_url, {"query": PROCESSES_QUERY})
        if processes.get("errors"):
            raise ValueError(f"GraphQL error: {processes['errors'][0].get('message')}")
        data = {"processes": len(processes["data"]["participatoryProcesses"] or [])}
        # Aggregate metrics are optional on older Decidim versions.
        try:
            metrics = self.post_json(city.decidim_api_url, {"query": METRICS_QUERY})
            for item in (metrics.get("data") or {}).get("metrics") or []:
                data[item["name"]] = int(item["count"])
        except Exception:
            pass
        return self.ok(data)

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        d = observation.data
        values = (ValueDimension.PARTICIPATORY, ValueDimension.DEMOCRATIC)
        metrics = [self.metric("participatory_processes", "Participatory processes", d["processes"], "processes",
                               log_scale(d["processes"], 1, 100), values=values)]
        if "participants" in d:
            metrics.append(self.metric("participation_participants", "Registered participants", d["participants"],
                                       "people", log_scale(d["participants"], 100, 100000), values=values))
        if "proposals" in d:
            metrics.append(self.metric("participation_proposals", "Citizen proposals", d["proposals"], "proposals",
                                       log_scale(d["proposals"], 10, 20000), values=values))
        return metrics
