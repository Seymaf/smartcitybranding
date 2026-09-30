"""Wikimedia Pageviews API: global research interest in the city (no key)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import List
from urllib.parse import quote

from connectors.base import BaseConnector, log_scale
from core.models import CityContext, NormalizedMetric, RawObservation, SmartCityComponent

PAGEVIEWS_URL = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
    "{project}/all-access/user/{article}/daily/{start}/{end}"
)
WINDOW_DAYS = 30


class WikimediaPageviewsConnector(BaseConnector):
    source_id = "wikimedia_pageviews"
    name = "Wikimedia Pageviews API"
    component = SmartCityComponent.TOURISM
    measurement_track = "Visitor Digital Interest"
    link = "https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html"

    def fetch(self, city: CityContext) -> RawObservation:
        end = datetime.now(timezone.utc).date() - timedelta(days=1)
        start = end - timedelta(days=WINDOW_DAYS - 1)
        url = PAGEVIEWS_URL.format(
            project=city.wikipedia_project,
            article=quote(city.wikipedia_title.replace(" ", "_"), safe=""),
            start=start.strftime("%Y%m%d"),
            end=end.strftime("%Y%m%d"),
        )
        views = [int(item["views"]) for item in self.get_json(url).get("items", [])]
        if not views:
            return self.no_data(f"no pageviews for {city.wikipedia_title!r}")
        recent, earlier = views[-7:], views[:-7] or views
        return self.ok({
            "article": f"{city.wikipedia_project}/{city.wikipedia_title}",
            "avg_daily_views": round(mean(views)),
            "last_7d_vs_prior": round(mean(recent) / mean(earlier) - 1, 3) if mean(earlier) else None,
            "days": len(views),
        })

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        d = observation.data
        return [self.metric(
            "wiki_interest", "Wikipedia daily views (30-day avg)", f"{d['avg_daily_views']:,} / day", "views",
            log_scale(d["avg_daily_views"], 100, 50000),
            note=f"Article {d['article']}, human traffic only.",
        )]
