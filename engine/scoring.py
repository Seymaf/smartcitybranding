"""Evidence-weighted scoring, the civic-values lens, and the integrity report.

Rules (documented in METHODOLOGY.md):
- A component is scored only from metrics that were actually obtained.
  No evidence -> no score (None), never a default number.
- Effective weight = metric weight x 0.5 if it is a national proxy.
  Curated metrics carry weight 0.5 and benchmarks 0.75 from their connectors,
  so live measurements dominate.
- Pillars follow the source map: each branding pillar averages the two smart
  city components mapped to it. The vitality index averages the pillars.
- The integrity report makes the greenwashing checks explicit.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from core.models import (
    BrandingPillar,
    CityBrandPulse,
    CityContext,
    ComponentScore,
    EvidenceType,
    GeoLevel,
    IntegrityFlag,
    NormalizedMetric,
    PillarScore,
    SmartCityComponent,
    SourceReport,
    SourceStatus,
    ValueDimension,
    ValueScore,
    utc_now_iso,
)

NATIONAL_PROXY_FACTOR = 0.5
CURATED_GAP_THRESHOLD = 25.0  # points a self-assessment may exceed the evidence
AIR_QUALITY_CONCERN = 50.0
# The headline vitality index is only called verifiable when at least half of
# the evidence weight is live-measured and every pillar has a score.
MIN_HEADLINE_MEASURED_SHARE = 0.5

COMPONENT_INFO: Dict[SmartCityComponent, Tuple[str, BrandingPillar]] = {
    SmartCityComponent.SMART_COMMUNICATION: ("Smart Communication", BrandingPillar.IDENTITY),
    SmartCityComponent.DIGITAL_INFRASTRUCTURE: ("Digital Infrastructure", BrandingPillar.IDENTITY),
    SmartCityComponent.E_GOVERNANCE: ("E-Governance", BrandingPillar.IMAGE),
    SmartCityComponent.TOURISM: ("Smart Tourism", BrandingPillar.IMAGE),
    SmartCityComponent.STAKEHOLDERS: ("Stakeholders", BrandingPillar.POSITIONING),
    SmartCityComponent.SUSTAINABILITY: ("Sustainability", BrandingPillar.POSITIONING),
}

PILLAR_NAMES = {
    BrandingPillar.IDENTITY: "City Identity",
    BrandingPillar.IMAGE: "City Image",
    BrandingPillar.POSITIONING: "City Positioning",
}

CURATED_SECTION_FOR = {
    SmartCityComponent.DIGITAL_INFRASTRUCTURE: "digital_infrastructure",
    SmartCityComponent.E_GOVERNANCE: "e_governance",
    SmartCityComponent.SMART_COMMUNICATION: "smart_communication",
    SmartCityComponent.STAKEHOLDERS: "stakeholders",
    SmartCityComponent.TOURISM: "local_events",
}


def effective_weight(metric: NormalizedMetric) -> float:
    factor = NATIONAL_PROXY_FACTOR if metric.geo_level == GeoLevel.NATIONAL_PROXY else 1.0
    return metric.weight * factor


def weighted_mean(metrics: Iterable[NormalizedMetric]) -> Optional[float]:
    pairs = [(effective_weight(m), m.score) for m in metrics]
    total = sum(w for w, _ in pairs)
    if total <= 0:
        return None
    return round(sum(w * s for w, s in pairs) / total, 1)


def _mean(values: Iterable[Optional[float]]) -> Optional[float]:
    present = [v for v in values if v is not None]
    return round(sum(present) / len(present), 1) if present else None


class BrandScoringEngine:
    def compute_pulse(
        self,
        city: CityContext,
        metrics: List[NormalizedMetric],
        sources: List[SourceReport],
        curated_data: Dict,
    ) -> CityBrandPulse:
        components = self._components(metrics, curated_data)
        pillars = self._pillars(components)
        values = self._values(metrics)
        ok_sources = sum(1 for s in sources if s.status == SourceStatus.OK)
        total_weight = sum(effective_weight(m) for m in metrics)
        measured_weight = sum(effective_weight(m) for m in metrics if m.evidence_type == EvidenceType.MEASURED)
        measured_share = round(measured_weight / total_weight, 3) if total_weight else 0.0
        verifiable = measured_share >= MIN_HEADLINE_MEASURED_SHARE and all(p.score is not None for p in pillars.values())
        flags = self._integrity(components, values, sources)
        if not verifiable:
            flags.insert(0, IntegrityFlag(
                "critical", "HEADLINE_NOT_VERIFIABLE",
                f"Only {measured_share:.0%} of the evidence is live-measured (minimum {MIN_HEADLINE_MEASURED_SHARE:.0%}) "
                "or a pillar has no evidence — do not publish the vitality index as a verified score."))
        return CityBrandPulse(
            city=city,
            timestamp=utc_now_iso(),
            vitality_index=_mean(p.score for p in pillars.values()),
            evidence_coverage=round(ok_sources / len(sources), 3) if sources else 0.0,
            measured_share=measured_share,
            headline_verifiable=verifiable,
            pillars={p.value: score for p, score in pillars.items()},
            components={c.value: score for c, score in components.items()},
            values={d.value: score for d, score in values.items()},
            integrity_flags=flags,
            sources=sources,
        )

    # ---- aggregation -------------------------------------------------------

    def _components(self, metrics: List[NormalizedMetric], curated: Dict) -> Dict[SmartCityComponent, ComponentScore]:
        result = {}
        for component, (display, pillar) in COMPONENT_INFO.items():
            own = [m for m in metrics if m.component == component]
            total = sum(effective_weight(m) for m in own)
            measured = sum(effective_weight(m) for m in own if m.evidence_type == EvidenceType.MEASURED)
            section = curated.get(CURATED_SECTION_FOR.get(component, ""), {}) if curated else {}
            result[component] = ComponentScore(
                component=component,
                display_name=display,
                score=weighted_mean(own),
                primary_pillar=pillar,
                metrics=own,
                measured_share=round(measured / total, 3) if total else 0.0,
                key_facts=list(section.get("key_facts", [])),
            )
        return result

    def _pillars(self, components: Dict[SmartCityComponent, ComponentScore]) -> Dict[BrandingPillar, PillarScore]:
        result = {}
        for pillar, display in PILLAR_NAMES.items():
            members = [c for c in components.values() if c.primary_pillar == pillar]
            result[pillar] = PillarScore(
                pillar=pillar,
                display_name=display,
                score=_mean(c.score for c in members),
                contributing_components=[c.component.value for c in members if c.score is not None],
            )
        return result

    def _values(self, metrics: List[NormalizedMetric]) -> Dict[ValueDimension, ValueScore]:
        result = {}
        for dimension in ValueDimension:
            tagged = [m for m in metrics if dimension in m.values]
            result[dimension] = ValueScore(
                dimension=dimension,
                score=weighted_mean(tagged),
                metrics=[f"{m.component.value}.{m.name}" for m in tagged],
            )
        return result

    # ---- integrity / greenwashing checks ----------------------------------

    def _integrity(
        self,
        components: Dict[SmartCityComponent, ComponentScore],
        values: Dict[ValueDimension, ValueScore],
        sources: List[SourceReport],
    ) -> List[IntegrityFlag]:
        flags: List[IntegrityFlag] = []
        for component, score in components.items():
            name = score.display_name
            if score.score is None:
                severity = "critical" if component == SmartCityComponent.SUSTAINABILITY else "warning"
                flags.append(IntegrityFlag(severity, "NO_EVIDENCE",
                                           f"{name}: no data from any source — not scored, and no claims should be made about it.",
                                           component.value))
                continue
            if score.measured_share == 0:
                flags.append(IntegrityFlag(
                    "critical" if component == SmartCityComponent.SUSTAINABILITY else "warning",
                    "SELF_REPORTED_ONLY",
                    f"{name}: scored only from curated assessments or published indices, with no live measurement to verify them.",
                    component.value))
            curated = [m for m in score.metrics if m.evidence_type == EvidenceType.CURATED]
            measured = [m for m in score.metrics if m.evidence_type == EvidenceType.MEASURED]
            if curated and measured:
                gap = (weighted_mean(curated) or 0) - (weighted_mean(measured) or 0)
                if gap > CURATED_GAP_THRESHOLD:
                    flags.append(IntegrityFlag("warning", "CURATED_ABOVE_EVIDENCE",
                                               f"{name}: the self-assessment is {gap:.0f} points above what live data shows.",
                                               component.value))

        sustainability = components[SmartCityComponent.SUSTAINABILITY]
        air = [m for m in sustainability.metrics if m.evidence_type == EvidenceType.MEASURED]
        air_score = weighted_mean(air)
        if air_score is not None and air_score < AIR_QUALITY_CONCERN:
            flags.append(IntegrityFlag("warning", "SUSTAINABILITY_GAP",
                                       f"Measured air quality scores {air_score}/100 — green or clean-air claims would not be supported today.",
                                       SmartCityComponent.SUSTAINABILITY.value))

        for dimension, value in values.items():
            if value.score is None:
                flags.append(IntegrityFlag("warning", "VALUE_UNEVIDENCED",
                                           f"No evidence for the '{dimension.value}' value dimension — do not claim it."))

        not_configured = [s.source_id for s in sources if s.status == SourceStatus.NOT_CONFIGURED]
        failed = [s.source_id for s in sources if s.status == SourceStatus.ERROR]
        if failed:
            flags.append(IntegrityFlag("info", "SOURCES_FAILED", f"Sources that failed this run: {', '.join(failed)}."))
        if not_configured:
            flags.append(IntegrityFlag("info", "SOURCES_NOT_CONFIGURED",
                                       f"Sources not configured (missing key or city endpoint): {', '.join(not_configured)}."))
        return flags
