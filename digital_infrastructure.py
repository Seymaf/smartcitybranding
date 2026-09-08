"""Fetches Bremen's digital infrastructure (internet speed/connectivity) data.

Combines two layers:
- A manually curated connectivity_score/key_facts audit in manual_data.json.
  There is no simple free real-time REST API for city-level internet speed
  comparable to OpenWeatherMap or TomTom: Ookla's live, queryable data
  lives behind the paid Speedtest Intelligence API, and its free
  alternative (Ookla Open Data on AWS) is a bulk historical dataset of
  Parquet tiles meant for offline analysis, not a per-city "give me
  today's number" endpoint.
- A live facility-presence signal from the PeeringDB API (free, no key
  required for read-only queries): how many internet exchange points and
  data-centre facilities are registered in Bremen right now. This is a
  proxy for infrastructure presence, not speed, but it's a genuinely live,
  queryable number where speed itself has none. Degrades gracefully to
  manual-only data if PeeringDB is unreachable.
"""

from __future__ import annotations

from typing import Any

import requests

from config import REQUEST_TIMEOUT, load_manual_data

PEERINGDB_FACILITIES_URL = "https://www.peeringdb.com/api/fac"
PEERINGDB_CITY = "Bremen"
PEERINGDB_COUNTRY = "DE"


def _score_from_facility_count(count: int) -> int:
    """Maps a registered-facility count to a rough 0-10 presence score.

    A simple bucketed heuristic, not a calibrated index — PeeringDB
    coverage skews toward facilities that actively peer/interconnect, so
    this reflects "presence in that ecosystem," not raw infrastructure
    density.
    """
    if count == 0:
        return 2
    if count == 1:
        return 5
    if count <= 3:
        return 7
    return 9


def _fetch_peeringdb_facilities() -> dict[str, Any] | None:
    """Fetches internet exchange/data-centre facilities registered in Bremen.

    Returns None on any failure (network error, non-2xx response, or
    unexpected payload shape) rather than raising — this is a nice-to-have
    live enrichment, not required for the pipeline to run.
    """
    try:
        response = requests.get(
            PEERINGDB_FACILITIES_URL,
            params={"city": PEERINGDB_CITY, "country": PEERINGDB_COUNTRY},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        facilities = payload["data"]
    except (requests.RequestException, ValueError, KeyError):
        return None

    names = [facility["name"] for facility in facilities if facility.get("name")]
    return {"facility_count": len(facilities), "names": names}


def fetch_digital_infrastructure() -> dict[str, Any]:
    """Returns Bremen's digital infrastructure data: manual audit + live PeeringDB facilities.

    Starts from the manually curated section of manual_data.json (fiber/5G
    rollout audit), then layers on a live "how many interconnection
    facilities does Bremen have registered right now" signal from
    PeeringDB. Falls back to manual data alone if PeeringDB is unreachable.
    """
    data = dict(load_manual_data("digital_infrastructure"))

    peeringdb = _fetch_peeringdb_facilities()
    if peeringdb is not None:
        data["infrastructure_presence_score"] = _score_from_facility_count(
            peeringdb["facility_count"]
        )
        data["key_facts"] = [
            *data.get("key_facts", []),
            f"Interconnection facilities registered in Bremen (PeeringDB): {peeringdb['facility_count']}",
            *(f"Facility: {name}" for name in peeringdb["names"]),
        ]

    return data
