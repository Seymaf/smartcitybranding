"""Runs the full Bremen City Pulse pipeline.

Fetches air quality (OpenWeatherMap) and traffic (TomTom) data for Bremen,
then uses the Anthropic Claude API to turn that data into a short, warm
daily "city pulse" summary.
"""

from __future__ import annotations

import sys
from datetime import datetime

import requests

from air_quality import fetch_air_quality
from city_pulse import generate_city_pulse
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

        print("Generating today's City Pulse with Claude...\n")
        summary = generate_city_pulse(air_quality, traffic)
    except requests.RequestException as exc:
        print(f"Error fetching data: {exc}", file=sys.stderr)
        return 1
    except (KeyError, IndexError) as exc:
        print(f"Unexpected API response format: {exc}", file=sys.stderr)
        return 1

    print("=" * 60)
    print(f"BREMEN CITY PULSE — {datetime.now().strftime('%A, %d %B %Y')}")
    print("=" * 60)
    print(summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())
