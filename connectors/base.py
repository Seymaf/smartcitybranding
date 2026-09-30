"""Base connector abstract class and resilient HTTP fetching utilities."""
from __future__ import annotations
import json, logging, urllib.parse, urllib.request
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from core.config import REQUEST_TIMEOUT, redact_secrets
from core.models import AccessTier, BrandingPillar, CityContext, NormalizedMetric, RawObservation, SmartCityComponent, UpdateCadence

logger = logging.getLogger(__name__)

class BaseConnector(ABC):
    source_id: str
    name: str
    component: SmartCityComponent
    pillar: BrandingPillar
    measurement_track: str
    cadence: UpdateCadence = UpdateCadence.DAILY
    is_realtime: bool = False
    access_tier: AccessTier = AccessTier.FREE_OPEN
    link: str = ""

    @abstractmethod
    def fetch(self, city: CityContext) -> RawObservation:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, observation: RawObservation) -> List[NormalizedMetric]:
        raise NotImplementedError

    def fallback(self, city: CityContext, error: Exception) -> RawObservation:
        safe_error = redact_secrets(str(error))
        return RawObservation(
            source_id=self.source_id,
            component=self.component,
            available=False,
            error=safe_error,
            data={},
            metadata={"status": "degraded_fallback"},
        )

    @staticmethod
    def http_get_json(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: int = REQUEST_TIMEOUT) -> Dict[str, Any]:
        try:
            import requests
            clean_params = {k: v for k, v in (params or {}).items() if v is not None}
            res = requests.get(url, params=clean_params, headers=headers or {}, timeout=timeout)
            res.raise_for_status()
            return res.json()
        except Exception:
            full_url = url
            if params:
                query_str = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
                delimiter = "&" if "?" in url else "?"
                full_url = f"{url}{delimiter}{query_str}"
            req = urllib.request.Request(
                full_url,
                headers={"User-Agent": "SmartCityBrandingEngine/2.0", **(headers or {})},
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content = response.read().decode("utf-8")
                return json.loads(content)
