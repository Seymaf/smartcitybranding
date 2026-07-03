"""Fetches today's flight arrivals at Bremen Airport (BRE) via AviationStack.

Represents a real-time "who is actually arriving right now" signal for the
tourism component, alongside (not replacing) traffic.py's road-flow data.

Three free-tier constraints shape this module:

- AviationStack's free plan is HTTP-only (HTTPS requires a paid plan), so
  the API key travels in the query string over plain HTTP. That's a
  limitation of AviationStack's own product tiering, not a choice made
  here — upgrade to a paid plan if that matters for your threat model.
- The `flight_date` query parameter is a paid-plan-only feature — the free
  plan returns `403 Forbidden` if it's included. This module doesn't send
  it at all; it relies on the endpoint's default behavior (a real-time
  snapshot of flights, which for arr_iata=BRE is effectively "today") and
  narrows to today client-side using each flight's own `flight_date` field
  in the response, which the free plan does return per record.
- The real-time /flights endpoint doesn't return a country field per
  flight, only the departure airport's name/IATA/ICAO/timezone. Resolving
  precise countries would mean a second lookup per unique departure
  airport against AviationStack's separate Airports endpoint, which would
  burn through the free tier's small monthly request quota fast. Instead,
  this module maps a best-effort static table of common IATA codes
  (covering Bremen's typical European/leisure route network) to country
  names, falling back to the airport's own name or IATA code for anything
  not in that table.

fetch_flight_arrivals() never raises — on any failure (missing API key,
rate limit, malformed response) it returns a summary dict with
`"available": False` and an `"error"` message, so a flaky third-party API
doesn't take down the rest of the pipeline.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from typing import Any

import requests

from config import AVIATIONSTACK_API_KEY, REQUEST_TIMEOUT

BREMEN_AIRPORT_IATA = "BRE"

# Free tier is HTTP-only; HTTPS requires a paid AviationStack plan.
FLIGHTS_URL = "http://api.aviationstack.com/v1/flights"

# Best-effort IATA -> country mapping for Bremen's typical route network.
# Not exhaustive: unmapped codes fall back to the departure airport's name.
IATA_TO_COUNTRY = {
    # United Kingdom
    "LHR": "United Kingdom",
    "LGW": "United Kingdom",
    "LTN": "United Kingdom",
    "STN": "United Kingdom",
    "LCY": "United Kingdom",
    "MAN": "United Kingdom",
    "EDI": "United Kingdom",
    "BHX": "United Kingdom",
    # Turkey
    "IST": "Turkey",
    "SAW": "Turkey",
    "AYT": "Turkey",
    "ADB": "Turkey",
    # Spain
    "BCN": "Spain",
    "MAD": "Spain",
    "PMI": "Spain",
    "AGP": "Spain",
    "ALC": "Spain",
    "TFS": "Spain",
    # Italy
    "FCO": "Italy",
    "MXP": "Italy",
    "BGY": "Italy",
    "VCE": "Italy",
    "NAP": "Italy",
    # France
    "CDG": "France",
    "ORY": "France",
    "NCE": "France",
    "BOD": "France",
    # Netherlands
    "AMS": "Netherlands",
    # Germany (domestic connections)
    "FRA": "Germany",
    "MUC": "Germany",
    "DUS": "Germany",
    "TXL": "Germany",
    "BER": "Germany",
    "HAM": "Germany",
    "CGN": "Germany",
    "STR": "Germany",
    "HAJ": "Germany",
    # Austria / Switzerland
    "VIE": "Austria",
    "SZG": "Austria",
    "ZRH": "Switzerland",
    "GVA": "Switzerland",
    "BSL": "Switzerland",
    # Southern / Eastern Europe leisure destinations
    "ATH": "Greece",
    "HER": "Greece",
    "RHO": "Greece",
    "LIS": "Portugal",
    "OPO": "Portugal",
    "FAO": "Portugal",
    "WAW": "Poland",
    "KRK": "Poland",
    "SPU": "Croatia",
    "DBV": "Croatia",
    "BOJ": "Bulgaria",
    "SOF": "Bulgaria",
    # North Africa charter destinations
    "HRG": "Egypt",
    "SSH": "Egypt",
    "RAK": "Morocco",
    "AGA": "Morocco",
    "DJE": "Tunisia",
    "MIR": "Tunisia",
    # Long-haul
    "DXB": "United Arab Emirates",
    "JFK": "United States",
    "EWR": "United States",
}


def _empty_summary(reason: str) -> dict[str, Any]:
    """Returns a degraded-but-valid summary when arrival data can't be fetched."""
    return {
        "available": False,
        "error": reason,
        "total_arrivals": 0,
        "origins": [],
        "notable_patterns": [f"Flight arrival data unavailable: {reason}"],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _resolve_origin(departure: dict[str, Any]) -> str:
    """Best-effort origin label for a flight's departure airport."""
    iata = (departure.get("iata") or "").upper()
    if iata in IATA_TO_COUNTRY:
        return IATA_TO_COUNTRY[iata]
    return departure.get("airport") or iata or "Unknown origin"


def fetch_flight_arrivals() -> dict[str, Any]:
    """Fetches and summarizes today's flight arrivals at Bremen Airport (BRE).

    Always returns a summary dict, even on failure — this component is a
    supplementary real-time signal, not a required input, so callers don't
    need to wrap this in their own try/except.
    """
    if not AVIATIONSTACK_API_KEY:
        return _empty_summary("AVIATIONSTACK_API_KEY is not set")

    try:
        response = requests.get(
            FLIGHTS_URL,
            params={
                # No flight_date here — it's a paid-plan-only parameter and
                # the free plan returns 403 Forbidden if it's included.
                "access_key": AVIATIONSTACK_API_KEY,
                "arr_iata": BREMEN_AIRPORT_IATA,
                "limit": 100,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        return _empty_summary(f"request failed ({exc})")
    except ValueError as exc:
        return _empty_summary(f"invalid response format ({exc})")

    if "error" in payload:
        api_error = payload["error"] or {}
        message = (
            api_error.get("message") or api_error.get("code") or "unknown API error"
        )
        return _empty_summary(str(message))

    all_flights = payload.get("data") or []
    fetched_at = datetime.now(timezone.utc).isoformat()

    # The free plan can't filter by date server-side, so narrow to today
    # using each flight's own flight_date field instead. Keep flights that
    # omit the field rather than drop them — the real-time endpoint only
    # returns a small, current window anyway.
    today = date.today().isoformat()
    flights = [f for f in all_flights if f.get("flight_date", today) == today]

    if not flights:
        return {
            "available": True,
            "error": None,
            "total_arrivals": 0,
            "origins": [],
            "notable_patterns": ["No arrivals recorded for today."],
            "fetched_at": fetched_at,
        }

    origin_counts: Counter[str] = Counter()
    for flight in flights:
        departure = flight.get("departure") or {}
        origin_counts[_resolve_origin(departure)] += 1

    ranked_origins = origin_counts.most_common()
    origins = [origin for origin, _count in ranked_origins]

    notable_patterns = [
        f"{count} arrival{'s' if count != 1 else ''} from {origin}"
        for origin, count in ranked_origins
        if count >= 2
    ]
    if not notable_patterns:
        notable_patterns = [
            f"{len(flights)} arrivals spread across {len(origins)} different "
            "origins, no single origin standing out today."
        ]

    return {
        "available": True,
        "error": None,
        "total_arrivals": len(flights),
        "origins": origins,
        "notable_patterns": notable_patterns,
        "fetched_at": fetched_at,
    }
