"""Published indices and rankings (benchmarks.json).

These sources have no live API; they publish annual/biennial reports or
downloadable datasets. Each entry in benchmarks.json stays `null` until
someone enters the value *together with* the edition year and a citation.
Entries without a value or citation are skipped, never guessed.
"""
from __future__ import annotations

from typing import List

from connectors.base import BaseConnector, linear
from core.config import BENCHMARKS_PATH, load_benchmarks
from core.models import (
    CityContext,
    EvidenceType,
    GeoLevel,
    NormalizedMetric,
    RawObservation,
    SmartCityComponent,
    UpdateCadence,
    ValueDimension,
)

BENCHMARK_WEIGHT = 0.75


def benchmark_score(entry: dict) -> float:
    scale = entry["scale"]
    value = float(entry["value"])
    if scale["type"] == "rank":
        return linear(value, scale["total"], 1)
    worst, best = (scale["min"], scale["max"]) if scale.get("higher_is_better", True) else (scale["max"], scale["min"])
    return linear(value, worst, best)


def is_filled(entry: dict) -> bool:
    if entry.get("value") is None or not entry.get("year") or not entry.get("citation"):
        return False
    return entry["scale"]["type"] != "rank" or bool(entry["scale"].get("total"))


class BenchmarksConnector(BaseConnector):
    source_id = "published_benchmarks"
    name = "Published indices & rankings (benchmarks.json)"
    component = SmartCityComponent.E_GOVERNANCE  # overridden per metric
    measurement_track = "Benchmark & Validation"
    link = "benchmarks.json"
    cadence = UpdateCadence.PERIODIC_BENCHMARK
    evidence_type = EvidenceType.BENCHMARK

    def fetch(self, city: CityContext) -> RawObservation:
        if not BENCHMARKS_PATH.exists():
            return self.no_data("benchmarks.json not found")
        entries = load_benchmarks().get("benchmarks", [])
        filled = [e for e in entries if is_filled(e)]
        if not filled:
            return self.no_data(f"none of the {len(entries)} benchmark entries has a cited value yet")
        return self.ok({"entries": filled, "pending": len(entries) - len(filled)})

    def normalize(self, observation: RawObservation, city: CityContext) -> List[NormalizedMetric]:
        metrics = []
        for e in observation.data["entries"]:
            metrics.append(self.metric(
                f"benchmark_{e['id']}", f"{e['name']} ({e['year']})", e["value"], e["scale"]["type"],
                benchmark_score(e),
                values=tuple(ValueDimension(v) for v in e.get("values", [])),
                weight=BENCHMARK_WEIGHT,
                note=e["citation"],
                source_url=e["link"],
                geo_level=GeoLevel(e.get("geo_level", "city")),
                component=SmartCityComponent(e["component"]),
            ))
        return metrics
