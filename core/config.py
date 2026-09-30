"""Central configuration management for the Smart City Branding platform."""
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
MANUAL_DATA_PATH = PROJECT_ROOT / "manual_data.json"
ARCHIVE_DIR = PROJECT_ROOT / "archive"
CACHE_PATH = PROJECT_ROOT / "cached_narratives.json"

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
TOMTOM_API_KEY = os.environ.get("TOMTOM_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
AVIATIONSTACK_API_KEY = os.environ.get("AVIATIONSTACK_API_KEY")
REQUEST_TIMEOUT = 12

SECRET_KEYS = [OPENWEATHER_API_KEY, TOMTOM_API_KEY, ANTHROPIC_API_KEY, AVIATIONSTACK_API_KEY]

def redact_secrets(text: str) -> str:
    if not text:
        return ""
    for secret in SECRET_KEYS:
        if secret and len(secret) > 4 and secret in text:
            text = text.replace(secret, "[REDACTED]")
    return text

def load_manual_data(section: str = "") -> Dict[str, Any]:
    if not MANUAL_DATA_PATH.exists():
        raise FileNotFoundError(f"{MANUAL_DATA_PATH} not found.")
    with open(MANUAL_DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    if section:
        if section not in data:
            raise KeyError(f"Section '{section}' not found in {MANUAL_DATA_PATH.name}")
        return data[section]
    return data
