"""Runs the full Bremen City Pulse pipeline.

Fetches data for Bremen's six smart city components — sustainability (air
quality), tourism (live traffic, real-time flight arrivals, and curated
local events), digital infrastructure, e-governance, smart communication,
and stakeholders — then uses the Anthropic Claude API to turn all of it
into three brand narratives: brand image, brand positioning, and brand
identity.
"""

from __future__ import annotations

import sys
from datetime import datetime

import requests

from air_quality import fetch_air_quality
from brand_engine import generate_brand_narratives
from config import REQUIRED_ENV_VARS
from digital_infrastructure import fetch_digital_infrastructure
from e_governance import fetch_e_governance
from flight_arrivals import fetch_flight_arrivals
from local_events import fetch_local_events
from smart_communication import fetch_smart_communication
from stakeholders import fetch_stakeholders
from traffic import fetch_traffic


def check_env() -> list[str]:
    return [name for name, value in REQUIRED_ENV_VARS.items() if not value]


def main() -> int:
    missing = check_env()
    if missing:
        print(
            f"Missing environment variables: {', '.join(missing)}.\n"
            "Copy .env.example to .env and fill in your API keys.",
            file=sys.stderr,
        )
        return 1

    try:
        print("Fetching air quality data from OpenWeatherMap (sustainability)...")
        air_quality = fetch_air_quality()

        print("Fetching tourism data (TomTom traffic + AviationStack arrivals + local events)...")
        traffic = fetch_traffic()
        flight_arrivals = fetch_flight_arrivals()
        if not flight_arrivals.get("available"):
            print(f"  (flight arrivals unavailable: {flight_arrivals.get('error')})")
        local_events = fetch_local_events()
        tourism = {
            "traffic": traffic,
            "flight_arrivals": flight_arrivals,
            "local_events": local_events,
        }

        print("Reading digital infrastructure data...")
        digital_infrastructure = fetch_digital_infrastructure()

        print("Reading e-governance data...")
        e_governance = fetch_e_governance()

        print("Reading smart communication data...")
        smart_communication = fetch_smart_communication()

        print("Reading stakeholders data...")
        stakeholders = fetch_stakeholders()

        print("Generating today's brand narratives with Claude...\n")
        narratives = generate_brand_narratives(
            air_quality=air_quality,
            tourism=tourism,
            digital_infrastructure=digital_infrastructure,
            e_governance=e_governance,
            smart_communication=smart_communication,
            stakeholders=stakeholders,
        )
    except requests.RequestException as exc:
        print(f"Error fetching data: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"Missing manual data file: {exc}", file=sys.stderr)
        return 1
    except (KeyError, IndexError) as exc:
        print(f"Unexpected data format: {exc}", file=sys.stderr)
        return 1

    print("=" * 60)
    print(f"BREMEN BRAND ENGINE — {datetime.now().strftime('%A, %d %B %Y')}")
    print("=" * 60)

    print("\n--- BRAND IMAGE ---")
    print(narratives.image)

    print("\n--- BRAND POSITIONING ---")
    print(narratives.positioning)

    print("\n--- BRAND IDENTITY ---")
    print(narratives.identity)

    return 0


if __name__ == "__main__":
    sys.exit(main())
