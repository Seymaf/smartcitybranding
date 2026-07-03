"""Shared configuration for the Bremen City Pulse pipeline."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# Bremen city center coordinates
BREMEN_LAT = 53.0793
BREMEN_LON = 8.8017

OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
TOMTOM_API_KEY = os.environ.get("TOMTOM_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

REQUEST_TIMEOUT = 15

REQUIRED_ENV_VARS = {
    "OPENWEATHER_API_KEY": OPENWEATHER_API_KEY,
    "TOMTOM_API_KEY": TOMTOM_API_KEY,
    "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
}
