"""Fetches Bremen's local events/festivals data.

No free real-time API exists for this component, so it reads from a manually
maintained section of manual_data.json — update that file directly to refresh
the values. This feeds into the tourism component alongside traffic.py and
flight_arrivals.py, rather than being a separate top-level component.
"""

from __future__ import annotations

from typing import Any

from config import load_manual_data


def fetch_local_events() -> dict[str, Any]:
    """Returns Bremen's local events data from manual_data.json."""
    return load_manual_data("local_events")
