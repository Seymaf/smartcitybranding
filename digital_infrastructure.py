"""Fetches Bremen's digital infrastructure (internet speed/connectivity) data.

There is no simple free real-time REST API for city-level internet speed
comparable to OpenWeatherMap or TomTom: Ookla's live, queryable data lives
behind the paid Speedtest Intelligence API, and its free alternative (Ookla
Open Data on AWS) is a bulk historical dataset of Parquet tiles meant for
offline analysis, not a per-city "give me today's number" endpoint. Given
that, this component follows the same manual_data.json pattern as
e_governance.py, smart_communication.py, and stakeholders.py.
"""

from __future__ import annotations

from typing import Any

from config import load_manual_data


def fetch_digital_infrastructure() -> dict[str, Any]:
    """Returns Bremen's digital infrastructure data from manual_data.json."""
    return load_manual_data("digital_infrastructure")
