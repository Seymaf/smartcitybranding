"""Google Places API (New) Text Search: visitor ratings for the city's attractions."""
from __future__ import annotations

from typing import List

from connectors.base import BaseConnector, linear, log_scale
from core.config import credential
from core.models import AccessTier, CityContext, NormalizedMetric, RawObservation, SmartCityComponent

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = "places.displayName,places.rating,places.userRatingCount"


class GooglePlacesConnector(BaseConnector):
    source_id = "google_places"
    name = "Google Places API"
    component = SmartCityComponent.TOURISM
    measurement_track = "Visitor Digital Interest"
    link = "https://developers.google.com/maps/documentation/places/web-service/overview"
    access_tier = AccessTier.FREEMIUM
    required_credentials = ("GOOGLE_PLACES_API_KEY",)

    def fetch(self, city: CityContext) -> RawObservation:
        payload = self.post_json(
            SEARCH_URL,
            {"textQuery": city.places_query, "pageSize": 20},
            headers={"X-Goog-Api-Key": credential("GOOGLE_PLACES_API_KEY"), "X-Goog-FieldMask": FIELD_MASK},
        )
        rated = [p for p in payload.get("places", []) if p.get("rating") and p.get("userRatingCount")]
        if not rated:
            return self.no_data(f"no rated places for {city.places_query!r}")
        reviews = sum(p["userRatingCount"] for p in rated)
        weighted = sum(p["rating"] * p["userRatingCount"] for p in rated) / reviews
        return self.ok({
            "places": len(rated),
            "reviews": reviews,
            "review_weighted_rating": round(weighted, 2),
            "top": [p.get("displayName", {}).get("text") for p in rated[:5]],
        })

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        d = observation.data
        return [
            self.metric("attraction_rating", "Attraction rating (review-weighted)", f"{d['review_weighted_rating']} / 5",
                        "stars", linear(d["review_weighted_rating"], 3.0, 5.0)),
            self.metric("attraction_reviews", "Attraction review volume", f"{d['reviews']:,} reviews", "reviews",
                        log_scale(d["reviews"], 1000, 1_000_000)),
        ]
