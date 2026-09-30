"""OpenSky Network: yesterday's arrivals at the city's airport (free, OAuth2).

OpenSky computes airport arrivals in a nightly batch, so the connector
queries the previous UTC day. API clients authenticate with the OAuth2
client-credentials flow (create a client in your OpenSky account).
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import List

import requests

from connectors.base import BaseConnector, linear, log_scale
from core.config import credential
from core.models import CityContext, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence

TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
ARRIVALS_URL = "https://opensky-network.org/api/flights/arrival"


class OpenSkyConnector(BaseConnector):
    source_id = "opensky_arrivals"
    name = "OpenSky Network API"
    component = SmartCityComponent.TOURISM
    measurement_track = "Air & Ground Arrivals"
    link = "https://openskynetwork.github.io/opensky-api/rest.html"
    cadence = UpdateCadence.DAILY
    required_credentials = ("OPENSKY_CLIENT_ID", "OPENSKY_CLIENT_SECRET")

    def fetch(self, city: CityContext) -> RawObservation:
        token = self.post_form(TOKEN_URL, {
            "grant_type": "client_credentials",
            "client_id": credential("OPENSKY_CLIENT_ID"),
            "client_secret": credential("OPENSKY_CLIENT_SECRET"),
        })["access_token"]
        day = datetime.now(timezone.utc).date() - timedelta(days=1)
        begin = datetime.combine(day, time.min, tzinfo=timezone.utc)
        try:
            flights = self.get_json(
                ARRIVALS_URL,
                {"airport": city.airport_icao, "begin": int(begin.timestamp()), "end": int((begin + timedelta(days=1)).timestamp())},
                headers={"Authorization": f"Bearer {token}"},
            )
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:  # OpenSky's "no flights"
                return self.no_data(f"no arrivals recorded at {city.airport_icao} on {day}")
            raise
        if not flights:
            return self.no_data(f"no arrivals recorded at {city.airport_icao} on {day}")
        departures = {f.get("estDepartureAirport") for f in flights if f.get("estDepartureAirport")}
        return self.ok({"airport": city.airport_icao, "date": day.isoformat(), "arrivals": len(flights), "departure_airports": len(departures)})

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        d = observation.data
        return [
            self.metric("opensky_arrivals", f"Arrivals on {d['date']}", f"{d['arrivals']} at {d['airport']}", "flights",
                        log_scale(d["arrivals"], 5, 1000)),
            self.metric("opensky_connectivity", "Distinct departure airports", d["departure_airports"], "airports",
                        linear(d["departure_airports"], 1, 60)),
        ]
