"""Central configuration: paths, API credentials, and secret redaction."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
MANUAL_DATA_PATH = PROJECT_ROOT / "manual_data.json"
BENCHMARKS_PATH = PROJECT_ROOT / "benchmarks.json"
ARCHIVE_DIR = PROJECT_ROOT / "archive"
CACHE_PATH = PROJECT_ROOT / "cached_narratives.json"

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

USER_AGENT = "SmartCityBranding/2.0 (+https://github.com/seymaf/smartcitybranding)"
REQUEST_TIMEOUT = 15

# Every credential is optional. A connector whose credential is missing
# reports itself as `not_configured` instead of failing the pipeline or
# inventing a substitute value.
CREDENTIAL_NAMES = [
    "ANTHROPIC_API_KEY",
    "OPENWEATHER_API_KEY",
    "OPENAQ_API_KEY",
    "AQICN_TOKEN",
    "TOMTOM_API_KEY",
    "AVIATIONSTACK_API_KEY",
    "OPENSKY_CLIENT_ID",
    "OPENSKY_CLIENT_SECRET",
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "ADZUNA_APP_ID",
    "ADZUNA_APP_KEY",
    "GOOGLE_PLACES_API_KEY",
    "OPENCELLID_API_KEY",
]


def credential(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def redact_secrets(text: str) -> str:
    """Strips every configured credential out of a string.

    HTTP error messages often embed the full request URL, query string
    included, which would otherwise leak keys passed as query parameters
    into logs or the git-tracked archive.
    """
    if not text:
        return ""
    for name in CREDENTIAL_NAMES:
        secret = credential(name)
        if secret and len(secret) > 4 and secret in text:
            text = text.replace(secret, "[REDACTED]")
    return text


def load_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{path.name} not found in {path.parent}.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_manual_data() -> Dict[str, Any]:
    return load_json_file(MANUAL_DATA_PATH)


def load_benchmarks() -> Dict[str, Any]:
    return load_json_file(BENCHMARKS_PATH)
