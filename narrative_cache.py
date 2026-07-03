"""Caches brand_positioning and brand_identity across pipeline runs.

brand_image is meant to regenerate every day — it's grounded in live
sustainability and tourism signals that change constantly, so there's no
sense caching it. brand_positioning and brand_identity, however, are
grounded mostly in manual_data.json's slower-moving components, so there's
no reason to pay for a fresh Claude call for those on every run.

This module fingerprints manual_data.json by its sections' last_updated
values. As long as none of them have changed since the cache was written,
the cached positioning/identity are still considered valid.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import MANUAL_DATA_PATH

CACHE_PATH = Path(__file__).parent / "cached_narratives.json"


def _current_manual_data_fingerprint() -> dict[str, Any]:
    """Maps each manual_data.json section to its last_updated value."""
    if not MANUAL_DATA_PATH.exists():
        return {}

    with open(MANUAL_DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    return {section: values.get("last_updated") for section, values in data.items()}


def load_cached_narratives() -> dict[str, Any] | None:
    """Returns the cached positioning/identity if present and still fresh.

    Returns None if there's no cache, the cache is malformed, or any
    manual_data.json section's last_updated has changed since the cache
    was written.
    """
    if not CACHE_PATH.exists():
        return None

    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    if "brand_positioning" not in cache or "brand_identity" not in cache:
        return None

    if cache.get("manual_data_fingerprint") != _current_manual_data_fingerprint():
        return None

    return cache


def save_cached_narratives(brand_positioning: str, brand_identity: str) -> None:
    """Writes brand_positioning/brand_identity plus a freshness fingerprint."""
    cache = {
        "brand_positioning": brand_positioning,
        "brand_identity": brand_identity,
        "manual_data_fingerprint": _current_manual_data_fingerprint(),
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
        f.write("\n")
