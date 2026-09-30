"""Reddit Data API (official, OAuth app-only): community discussion volume."""
from __future__ import annotations

from statistics import mean
from typing import List

from connectors.base import BaseConnector, linear, log_scale
from core.config import credential
from core.models import CityContext, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
SEARCH_URL = "https://oauth.reddit.com/search"


class RedditConnector(BaseConnector):
    source_id = "reddit_data_api"
    name = "Reddit Data API"
    component = SmartCityComponent.SMART_COMMUNICATION
    measurement_track = "Public Perception"
    link = "https://www.reddit.com/dev/api/"
    cadence = UpdateCadence.INTRA_HOUR
    required_credentials = ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET")

    def fetch(self, city: CityContext) -> RawObservation:
        token = self.post_form(
            TOKEN_URL,
            {"grant_type": "client_credentials"},
            auth=(credential("REDDIT_CLIENT_ID"), credential("REDDIT_CLIENT_SECRET")),
        )["access_token"]
        payload = self.get_json(
            SEARCH_URL,
            {"q": city.reddit_query, "t": "week", "sort": "new", "limit": 100, "type": "link"},
            headers={"Authorization": f"bearer {token}"},
        )
        posts = [child["data"] for child in payload.get("data", {}).get("children", [])]
        if not posts:
            return self.no_data(f"no posts matched {city.reddit_query!r} this week")
        ratios = [p["upvote_ratio"] for p in posts if p.get("upvote_ratio") is not None]
        return self.ok({
            "posts": len(posts),
            "capped_at_100": len(posts) >= 100,
            "comments": sum(p.get("num_comments", 0) for p in posts),
            "subreddits": len({p.get("subreddit") for p in posts}),
            "mean_upvote_ratio": round(mean(ratios), 3) if ratios else None,
        })

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        data = observation.data
        posts_label = f"{data['posts']}{'+' if data['capped_at_100'] else ''} posts / week"
        metrics = [self.metric("reddit_volume", "Community discussion volume", posts_label, "posts",
                               log_scale(data["posts"], 5, 100),
                               note="One search page (max 100 posts); 100 means 'at least 100'.")]
        if data.get("mean_upvote_ratio") is not None:
            metrics.append(self.metric(
                "reddit_reception", "Community reception (upvote ratio)", data["mean_upvote_ratio"], "ratio",
                linear(data["mean_upvote_ratio"], 0.5, 1.0),
                note="Upvote ratio is a reception proxy, not sentiment analysis.",
            ))
        return metrics
