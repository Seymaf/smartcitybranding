"""Shared configuration for the Bremen City Pulse pipeline."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# Bremen city center coordinates
BREMEN_LAT = 53.0793
BREMEN_LON = 8.8017

OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
TOMTOM_API_KEY = os.environ.get("TOMTOM_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Optional: powers flight_arrivals.py. Not in REQUIRED_ENV_VARS because that
# module degrades gracefully (returns an "unavailable" summary) rather than
# failing the whole pipeline when this key is missing or rate-limited.
AVIATIONSTACK_API_KEY = os.environ.get("AVIATIONSTACK_API_KEY")

REQUEST_TIMEOUT = 15

REQUIRED_ENV_VARS = {
    "OPENWEATHER_API_KEY": OPENWEATHER_API_KEY,
    "TOMTOM_API_KEY": TOMTOM_API_KEY,
    "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
}

# Manually maintained smart city data (no free real-time API available for
# these components). Edit manual_data.json directly to update them.
MANUAL_DATA_PATH = Path(__file__).parent / "manual_data.json"


def load_manual_data(section: str) -> dict[str, Any]:
    """Loads one top-level section (e.g. "e_governance") from manual_data.json."""
    if not MANUAL_DATA_PATH.exists():
        raise FileNotFoundError(
            f"{MANUAL_DATA_PATH.name} not found. Create it in the project root "
            "with sections for digital_infrastructure, e_governance, "
            "smart_communication, and stakeholders."
        )

    with open(MANUAL_DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    if section not in data:
        raise KeyError(
            f"'{section}' section not found in {MANUAL_DATA_PATH.name}. "
            f"Available sections: {', '.join(data.keys())}"
        )

    return data[section]
