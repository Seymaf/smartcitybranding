"""Fetches Bremen's Wikipedia pageview trend as a visitor-digital-interest signal.

Feeds into the tourism component alongside traffic.py, flight_arrivals.py,
and local_events.py. Wikimedia's Pageviews API is free, needs no API key,
and is a reasonable free proxy for global research/travel interest in
Bremen — how many people are looking the city up on a given day.

fetch_wikipedia_interest() never raises — like flight_arrivals.py, this is
a supplementary live signal, not a required input, so on any failure it
returns a summary dict with "available": False instead of taking down the
rest of the pipeline.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from config import REQUEST_TIMEOUT

WIKIPEDIA_ARTICLE = "Bremen"
PAGEVIEWS_URL = (
    f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
    f"en.wikipedia/all-access/user/{WIKIPEDIA_ARTICLE}/daily/{{start}}/{{end}}"
)

# Wikimedia asks API consumers to identify themselves via User-Agent.
HEADERS = {"User-Agent": "BremenCityPulse/1.0 (smart city branding pipeline)"}

# Pageview counts usually aren't finalized for the last day or two, so this
# looks at a 7-day window ending 2 days ago rather than "today".
LAG_DAYS = 2
WINDOW_DAYS = 7


def _empty_summary(reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "error": reason,
        "total_views_7d": 0,
        "daily_average": 0,
        "latest_day_views": 0,
    }


def fetch_wikipedia_interest() -> dict[str, Any]:
    """Fetches Bremen's English Wikipedia pageviews over the last available week."""
    end_date = datetime.now(timezone.utc) - timedelta(days=LAG_DAYS)
    start_date = end_date - timedelta(days=WINDOW_DAYS - 1)
    url = PAGEVIEWS_URL.format(
        start=start_date.strftime("%Y%m%d") + "00",
        end=end_date.strftime("%Y%m%d") + "00",
    )

    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        items = response.json()["items"]
    except requests.RequestException as exc:
        return _empty_summary(f"request failed ({exc})")
    except (ValueError, KeyError) as exc:
        return _empty_summary(f"invalid response format ({exc})")

    if not items:
        return _empty_summary("no pageview data returned for this window")

    daily_views = [item["views"] for item in items]
    total = sum(daily_views)

    return {
        "available": True,
        "error": None,
        "total_views_7d": total,
        "daily_average": round(total / len(daily_views)),
        "latest_day_views": daily_views[-1],
        "window_end": end_date.strftime("%Y-%m-%d"),
    }
