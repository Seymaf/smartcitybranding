"""Base connector and shared HTTP / normalization helpers.

Contract every connector follows (this is the anti-greenwashing rule set):

1. `fetch()` either returns real data from the source, or the run records
   the source as `not_configured`, `error` or `no_data`. There are no
   "baseline estimators" or simulated fallbacks: a missing source produces
   no metrics, and the scoring engine scores only what was actually seen.
2. Every metric carries its source, URL, retrieval time, evidence type and
   geographic level, so any claim built on it can be traced back.
"""
from __future__ import annotations

import logging
import math
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import requests

from core.config import REQUEST_TIMEOUT, USER_AGENT, credential, redact_secrets
from core.models import (
    AccessTier,
    CityContext,
    EvidenceType,
    GeoLevel,
    NormalizedMetric,
    RawObservation,
    SmartCityComponent,
    SourceStatus,
    UpdateCadence,
    ValueDimension,
)

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    source_id: str
    name: str
    component: SmartCityComponent
    measurement_track: str
    link: str
    cadence: UpdateCadence = UpdateCadence.DAILY
    access_tier: AccessTier = AccessTier.FREE_OPEN
    geo_level: GeoLevel = GeoLevel.CITY
    evidence_type: EvidenceType = EvidenceType.MEASURED
    required_credentials: Tuple[str, ...] = ()

    # ---- lifecycle -------------------------------------------------------

    def missing_configuration(self, city: CityContext) -> Optional[str]:
        """Returns a human-readable reason if this source can't run, else None."""
        missing = [name for name in self.required_credentials if not credential(name)]
        if missing:
            return f"missing credential(s): {', '.join(missing)}"
        return None

    @abstractmethod
    def fetch(self, city: CityContext) -> RawObservation:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        raise NotImplementedError

    def run(self, city: CityContext) -> Tuple[RawObservation, List[NormalizedMetric]]:
        reason = self.missing_configuration(city)
        if reason:
            return self._observation(SourceStatus.NOT_CONFIGURED, error=reason), []
        try:
            observation = self.fetch(city)
            if not observation.available:
                return observation, []
            return observation, self.normalize(observation, city)
        except Exception as exc:  # any source failure must not stop the pipeline
            message = redact_secrets(f"{type(exc).__name__}: {exc}")[:300]
            logger.info("%s failed: %s", self.source_id, message)
            return self._observation(SourceStatus.ERROR, error=message), []

    # ---- builders --------------------------------------------------------

    def _observation(self, status: SourceStatus, data: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> RawObservation:
        return RawObservation(source_id=self.source_id, component=self.component, status=status, data=data or {}, error=error)

    def ok(self, data: Dict[str, Any]) -> RawObservation:
        return self._observation(SourceStatus.OK, data=data)

    def no_data(self, reason: str, data: Optional[Dict[str, Any]] = None) -> RawObservation:
        return self._observation(SourceStatus.NO_DATA, data=data, error=reason)

    def metric(
        self,
        name: str,
        display_name: str,
        raw_value: Any,
        unit: str,
        score: float,
        values: Tuple[ValueDimension, ...] = (),
        weight: float = 1.0,
        note: str = "",
        source_url: Optional[str] = None,
        geo_level: Optional[GeoLevel] = None,
        evidence_type: Optional[EvidenceType] = None,
        component: Optional[SmartCityComponent] = None,
    ) -> NormalizedMetric:
        return NormalizedMetric(
            name=name,
            display_name=display_name,
            raw_value=raw_value,
            unit=unit,
            score=round(clamp(score), 1),
            source_id=self.source_id,
            source_url=source_url or self.link,
            component=component or self.component,
            evidence_type=evidence_type or self.evidence_type,
            geo_level=geo_level or self.geo_level,
            weight=weight,
            values=list(values),
            note=note,
        )

    # ---- HTTP ------------------------------------------------------------

    @staticmethod
    def _headers(headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        return {"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})}

    @classmethod
    def get_json(cls, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, auth: Any = None) -> Any:
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        response = requests.get(url, params=clean, headers=cls._headers(headers), auth=auth, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()

    @classmethod
    def post_json(cls, url: str, payload: Any, headers: Optional[Dict[str, str]] = None) -> Any:
        response = requests.post(url, json=payload, headers=cls._headers(headers), timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()

    @classmethod
    def post_form(cls, url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None, auth: Any = None) -> Any:
        response = requests.post(url, data=data, headers=cls._headers(headers), auth=auth, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()


# ---- normalization helpers (all return 0-100) ------------------------------


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(value)))


def linear(value: float, worst: float, best: float) -> float:
    """Maps `worst` -> 0 and `best` -> 100 linearly (works for inverted scales)."""
    if best == worst:
        return 0.0
    return clamp((float(value) - worst) / (best - worst) * 100.0)


def log_scale(value: float, low: float, high: float) -> float:
    """Maps volumes on a log scale: `low` -> 0, `high` -> 100.

    Volume signals (articles, pageviews, datasets, job ads) span orders of
    magnitude between small and large cities, so a log scale keeps one very
    large number from saturating the score.
    """
    if value <= 0:
        return 0.0
    return linear(math.log10(value), math.log10(low), math.log10(high))
