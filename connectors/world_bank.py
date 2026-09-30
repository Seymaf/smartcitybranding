"""Shared World Bank Indicators API (v2) helper — no key required.

The Worldwide Governance Indicators were re-coded in the 2024 revision
(e.g. `VA.EST` became `GOV_WGI_VA.EST` in some releases), so each indicator
lists the codes to try in order.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from connectors.base import BaseConnector

API_URL = "https://api.worldbank.org/v2/country/{iso3}/indicator/{code}"


@dataclass
class IndicatorValue:
    code: str
    year: str
    value: float


def latest_value(iso3: str, codes: Sequence[str], source: int) -> Optional[IndicatorValue]:
    """Returns the most recent non-empty value for the first code that resolves."""
    for code in codes:
        payload = BaseConnector.get_json(
            API_URL.format(iso3=iso3, code=code),
            {"format": "json", "source": source, "mrnev": 1},
        )
        # Success: [meta, [rows]]. Unknown code: [{"message": [...]}].
        if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
            continue
        row = payload[1][0]
        if row.get("value") is None:
            continue
        return IndicatorValue(code=code, year=str(row.get("date")), value=float(row["value"]))
    return None


IndicatorSpec = Tuple[str, str, Tuple[str, ...]]  # (metric name, display name, codes)
