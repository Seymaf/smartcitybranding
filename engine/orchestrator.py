"""Runs every connector, scores the evidence, writes narratives, archives the day."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import date
from enum import Enum
from pathlib import Path
from typing import List, Optional

from connectors.base import BaseConnector
from connectors.registry import default_connectors
from core.config import ARCHIVE_DIR, MANUAL_DATA_PATH, load_manual_data, redact_secrets
from core.models import CityBrandPulse, CityContext, NormalizedMetric, SourceReport
from engine.brand_narrator import BrandNarrator, slow_evidence_fingerprint
from engine.narrative_cache import load_cached, save_cached
from engine.scoring import BrandScoringEngine

logger = logging.getLogger(__name__)


class CityBrandOrchestrator:
    def __init__(self, city: Optional[CityContext] = None, connectors: Optional[List[BaseConnector]] = None) -> None:
        self.city = city or CityContext()
        self.connectors = connectors if connectors is not None else default_connectors()
        self.scoring_engine = BrandScoringEngine()
        self.narrator = BrandNarrator()

    def collect(self):
        metrics: List[NormalizedMetric] = []
        sources: List[SourceReport] = []
        raw = {}
        for connector in self.connectors:
            observation, produced = connector.run(self.city)
            metrics.extend(produced)
            raw[connector.source_id] = asdict(observation)
            sources.append(SourceReport(
                source_id=connector.source_id,
                name=connector.name,
                component=connector.component,
                status=observation.status,
                link=connector.link,
                access_tier=connector.access_tier,
                metrics=len(produced),
                error=observation.error,
            ))
        return metrics, sources, raw

    def run_pipeline(self, with_narratives: bool = True, force_refresh: bool = False) -> tuple[CityBrandPulse, dict]:
        metrics, sources, raw = self.collect()
        curated = load_manual_data() if MANUAL_DATA_PATH.exists() else {}
        pulse = self.scoring_engine.compute_pulse(self.city, metrics, sources, curated)

        if with_narratives and self.narrator.enabled:
            try:
                self._add_narratives(pulse, force_refresh)
            except Exception as exc:  # a Claude outage must not lose the day's evidence
                logger.error("Narrative generation failed: %s", redact_secrets(str(exc)))
        return pulse, raw

    def _add_narratives(self, pulse: CityBrandPulse, force_refresh: bool) -> None:
        image = self.narrator.brand_image(pulse)
        if image:
            pulse.narratives["brand_image"] = image
        fingerprint = slow_evidence_fingerprint(pulse)
        cached = None if force_refresh else load_cached(fingerprint)
        if cached:
            pulse.narratives.update(cached)
        else:
            fresh = self.narrator.positioning_and_identity(pulse)
            if fresh:
                pulse.narratives.update(fresh)
                save_cached(fingerprint, fresh)


def _json_default(obj):
    if isinstance(obj, Enum):
        return obj.value
    return str(obj)


def save_archive(pulse: CityBrandPulse, raw: dict) -> Path:
    """Writes archive/<YYYY-MM-DD>.json (one snapshot per day, overwritten per run)."""
    ARCHIVE_DIR.mkdir(exist_ok=True)
    path = ARCHIVE_DIR / f"{date.today().isoformat()}.json"
    payload = {"pulse": asdict(pulse), "raw_observations": raw}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default) + "\n", encoding="utf-8")
    return path
