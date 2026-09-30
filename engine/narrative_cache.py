"""Caches brand_positioning and brand_identity across runs.

brand_image regenerates every run. Positioning and identity rest on the
slow-moving evidence (curated data, benchmarks, annual indicators), so a
fresh Claude call is only made when that evidence's fingerprint changes.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Dict, Optional

from core.config import CACHE_PATH
from core.models import BrandingPillar, BrandNarrative, utc_now_iso


def load_cached(fingerprint: Dict[str, str]) -> Optional[Dict[str, BrandNarrative]]:
    if not CACHE_PATH.exists():
        return None
    try:
        cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        if cache.get("fingerprint") != fingerprint:
            return None
        narratives = {}
        for key in ("brand_positioning", "brand_identity"):
            item = dict(cache["narratives"][key])
            item["pillar"] = BrandingPillar(item["pillar"])
            item["status"] = "cached"
            narratives[key] = BrandNarrative(**item)
        return narratives
    except (OSError, ValueError, KeyError, TypeError):
        return None


def save_cached(fingerprint: Dict[str, str], narratives: Dict[str, BrandNarrative]) -> None:
    payload = {
        "fingerprint": fingerprint,
        "cached_at": utc_now_iso(),
        "narratives": {k: asdict(v) for k, v in narratives.items()},
    }
    CACHE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
