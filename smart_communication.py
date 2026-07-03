"""Fetches Bremen's smart communication data.

No free real-time API exists for this component, so it reads from a manually
maintained section of manual_data.json — update that file directly to refresh
the values.
"""

from __future__ import annotations

from typing import Any

from config import load_manual_data


def fetch_smart_communication() -> dict[str, Any]:
    """Returns Bremen's smart communication data from manual_data.json."""
    return load_manual_data("smart_communication")
