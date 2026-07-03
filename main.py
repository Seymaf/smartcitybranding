"""Runs the full Bremen City Pulse pipeline.

Fetches air quality (OpenWeatherMap) and traffic (TomTom) data for Bremen,
then uses the Anthropic Claude API to turn that data into three brand
narratives: brand image, brand positioning, and brand identity.
"""

from __future__ import annotations

import sys
from datetime import datetime

import requests

from air_quality import fetch_air_quality
from brand_engine import generate_brand_narratives
from config import REQUIRED_ENV_VARS
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
        print("Fetching air quality data from OpenWeatherMap...")
        air_quality = fetch_air_quality()

        print("Fetching traffic data from TomTom...")
        traffic = fetch_traffic()

        print("Generating today's brand narratives with Claude...\n")
        narratives = generate_brand_narratives(air_quality, traffic)
    except requests.RequestException as exc:
        print(f"Error fetching data: {exc}", file=sys.stderr)
        return 1
    except (KeyError, IndexError) as exc:
        print(f"Unexpected API response format: {exc}", file=sys.stderr)
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
