"""AviationStack: today's real-time arrivals at the city's airport.

Free-tier constraints (carried over from the original flight_arrivals.py):
- the free plan is HTTP-only, so the key travels in the query string over
  plain HTTP — an AviationStack product limitation;
- `flight_date` is a paid-only parameter (403 on free), so today's flights
  are filtered client-side from each record's own `flight_date`;
- there's no country per flight, so a static IATA -> country table covers
  the typical route network and anything else falls back to the airport name.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any, Dict, List

from connectors.base import BaseConnector, linear, log_scale
from core.config import credential
from core.models import AccessTier, CityContext, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence

FLIGHTS_URL = "http://api.aviationstack.com/v1/flights"

IATA_TO_COUNTRY = {
    **dict.fromkeys(["LHR", "LGW", "LTN", "STN", "LCY", "MAN", "EDI", "BHX"], "United Kingdom"),
    **dict.fromkeys(["IST", "SAW", "AYT", "ADB"], "Turkey"),
    **dict.fromkeys(["BCN", "MAD", "PMI", "AGP", "ALC", "TFS"], "Spain"),
    **dict.fromkeys(["FCO", "MXP", "BGY", "VCE", "NAP"], "Italy"),
    **dict.fromkeys(["CDG", "ORY", "NCE", "BOD"], "France"),
    "AMS": "Netherlands",
    **dict.fromkeys(["FRA", "MUC", "DUS", "BER", "HAM", "CGN", "STR", "HAJ"], "Germany"),
    **dict.fromkeys(["VIE", "SZG"], "Austria"),
    **dict.fromkeys(["ZRH", "GVA", "BSL"], "Switzerland"),
    **dict.fromkeys(["ATH", "HER", "RHO"], "Greece"),
    **dict.fromkeys(["LIS", "OPO", "FAO"], "Portugal"),
    **dict.fromkeys(["WAW", "KRK"], "Poland"),
    **dict.fromkeys(["SPU", "DBV"], "Croatia"),
    **dict.fromkeys(["BOJ", "SOF"], "Bulgaria"),
    **dict.fromkeys(["HRG", "SSH"], "Egypt"),
    **dict.fromkeys(["RAK", "AGA"], "Morocco"),
    **dict.fromkeys(["DJE", "MIR"], "Tunisia"),
    "DXB": "United Arab Emirates",
    **dict.fromkeys(["JFK", "EWR"], "United States"),
}


def resolve_origin(departure: Dict[str, Any]) -> str:
    iata = (departure.get("iata") or "").upper()
    return IATA_TO_COUNTRY.get(iata) or departure.get("airport") or iata or "Unknown origin"


class AviationStackConnector(BaseConnector):
    source_id = "aviationstack_arrivals"
    name = "Aviationstack (APILayer)"
    component = SmartCityComponent.TOURISM
    measurement_track = "Air & Ground Arrivals"
    link = "https://aviationstack.com/"
    cadence = UpdateCadence.INTRA_HOUR
    access_tier = AccessTier.FREEMIUM
    required_credentials = ("AVIATIONSTACK_API_KEY",)

    def fetch(self, city: CityContext) -> RawObservation:
        payload = self.get_json(FLIGHTS_URL, {
            "access_key": credential("AVIATIONSTACK_API_KEY"),
            "arr_iata": city.airport_iata,
            "limit": 100,
        })
        if payload.get("error"):
            err = payload["error"] or {}
            raise ValueError(err.get("message") or err.get("code") or "unknown AviationStack error")
        today = date.today().isoformat()
        flights = [f for f in payload.get("data") or [] if f.get("flight_date", today) == today]
        if not flights:
            return self.no_data(f"no arrivals recorded today at {city.airport_iata}")
        origins = Counter(resolve_origin(f.get("departure") or {}) for f in flights)
        return self.ok({
            "airport": city.airport_iata,
            "arrivals_today": len(flights),
            "origins": dict(origins.most_common()),
        })

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        d = observation.data
        return [
            self.metric("arrivals_today", "Flight arrivals today", f"{d['arrivals_today']} at {d['airport']}", "flights",
                        log_scale(d["arrivals_today"], 5, 500),
                        note="Real-time endpoint returns a single page (max 100)."),
            self.metric("arrival_origins", "Distinct arrival origins today", len(d["origins"]), "origins",
                        linear(len(d["origins"]), 1, 20)),
        ]
