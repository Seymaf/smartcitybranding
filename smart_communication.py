"""Fetches Bremen's smart communication data.

Combines two layers:
- Manually curated facts about Bremen's own citizen-facing communication
  channels and conversational-AI ecosystem (chatbots, social accounts) —
  read from manual_data.json, since no API measures "citizen engagement
  quality" for a city's own channels; that's a judgment-based audit.
- A live public-perception signal from the GDELT DOC 2.0 API: how much
  Bremen is mentioned in global news right now, and with which headlines.
  GDELT needs no API key/signup, but this still degrades gracefully to
  manual-only data if the request fails, since it's an enrichment on top
  of the manual audit, not a replacement for it.
"""

from __future__ import annotations

from typing import Any

import requests

from config import REQUEST_TIMEOUT, load_manual_data

GDELT_DOC_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
# Both terms required (GDELT space-separates as AND) to avoid matching the
# unrelated small towns also named Bremen in the US (Georgia, Indiana, Ohio).
GDELT_QUERY = "Bremen Germany"


def _score_from_mention_count(count: int) -> int:
    """Maps a 24h global news mention count to a rough 0-10 visibility score.

    A simple bucketed heuristic, not a calibrated index — GDELT indexes a
    huge and growing set of outlets, so what counts as "a lot" of mentions
    for a city Bremen's size is a judgment call, not a formula.
    """
    if count == 0:
        return 2
    if count <= 5:
        return 4
    if count <= 15:
        return 6
    if count <= 40:
        return 8
    return 10


def _fetch_gdelt_mentions() -> dict[str, Any] | None:
    """Fetches the last 24h of global news mentions of Bremen from GDELT.

    Returns None on any failure (network error, non-2xx response, or
    unexpected payload shape) rather than raising — this is a nice-to-have
    live enrichment, not required for the pipeline to run.
    """
    try:
        response = requests.get(
            GDELT_DOC_API_URL,
            params={
                "query": GDELT_QUERY,
                "mode": "artlist",
                "format": "json",
                "maxrecords": 50,
                "timespan": "1d",
                "sort": "datedesc",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        articles = payload["articles"]
    except (requests.RequestException, ValueError, KeyError):
        return None

    headlines = [
        f"{article['title']} ({article.get('domain', 'unknown source')})"
        for article in articles[:3]
        if article.get("title")
    ]

    return {"mention_count_24h": len(articles), "headlines": headlines}


def fetch_smart_communication() -> dict[str, Any]:
    """Returns Bremen's smart communication data: manual audit + live GDELT mentions.

    Starts from the manually curated section of manual_data.json (Bremen's
    own chatbot/social-media ecosystem), then layers on a live "how much is
    Bremen in the news right now" signal as an additional metric and a
    couple of key_facts. Falls back to manual data alone if GDELT is
    unreachable.
    """
    data = dict(load_manual_data("smart_communication"))

    gdelt = _fetch_gdelt_mentions()
    if gdelt is not None:
        data["media_visibility_score"] = _score_from_mention_count(gdelt["mention_count_24h"])
        data["key_facts"] = [
            *data.get("key_facts", []),
            f"Global news mentions of Bremen in the last 24h: {gdelt['mention_count_24h']} (via GDELT)",
            *(f"Recent headline: {headline}" for headline in gdelt["headlines"]),
        ]

    return data
