"""Brand narratives written by Claude, grounded in an explicit evidence ledger.

Anti-greenwashing by construction:
- Claude sees only the metrics that were actually obtained this run, each
  with an id, its evidence type (measured / benchmark / curated) and its
  geographic level, plus the integrity flags.
- Every narrative must return the ids of the metrics it relies on; ids that
  don't exist in the ledger are surfaced as warnings on the narrative.
- Without an API key, or without any evidence, no narrative is produced —
  there is no canned fallback text.

brand_image regenerates every run (live signals). brand_positioning and
brand_identity are cached until the slow-moving evidence (curated data,
published benchmarks, annual indicators) changes — see narrative_cache.py.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional

from core.config import credential
from core.models import BrandingPillar, BrandNarrative, CityBrandPulse, EvidenceType, GeoLevel, utc_now_iso

logger = logging.getLogger(__name__)

MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """You are the brand strategist of a company whose mission is to \
identify cities and global brands that protect democratic, participatory and \
innovative values, and to show their brand value without greenwashing.

You turn an evidence ledger about one city into brand narratives. The ledger is \
the only thing you know about the city today. Work by these rules:

- Every factual statement must rest on a ledger entry, and you must list the ids \
of the entries you used. If the ledger doesn't support a claim, leave it out.
- Say what kind of evidence a claim rests on when it matters: "measured" entries \
are live data from this run; "benchmark" entries are published indices; \
"curated" entries are the city's own or our analysts' assessments and must be \
framed as assessments, not as proven facts. National-proxy entries describe the \
country, not the city, and must be framed that way.
- Respect the integrity flags. Where a component has no evidence or only \
self-reported evidence, make no claims about it (or only clearly hedged ones for \
self-reported evidence). Never make environmental or climate claims unless \
measured sustainability entries support them.
- If headline_verifiable is false, don't cite the vitality index or pillar scores \
as verified results.
- Concrete numbers beat adjectives. No generic city-marketing superlatives.
- Don't discuss data outages or missing sources in the narrative text itself; \
simply don't write about what isn't there."""


def _schema(fields: List[str]) -> dict:
    narrative = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "cited_metrics": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["text", "cited_metrics"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {f: narrative for f in fields},
        "required": fields,
        "additionalProperties": False,
    }


def evidence_ledger(pulse: CityBrandPulse) -> Dict[str, dict]:
    ledger = {}
    for component in pulse.components.values():
        for m in component.metrics:
            ledger[f"{component.component.value}.{m.name}"] = {
                "label": m.display_name,
                "value": m.raw_value,
                "unit": m.unit,
                "score_0_100": m.score,
                "evidence": m.evidence_type.value,
                "geo": m.geo_level.value,
                "source": m.source_id,
                "note": m.note,
            }
    return ledger


def _data_block(pulse: CityBrandPulse, ledger: Dict[str, dict]) -> str:
    summary = {
        "city": f"{pulse.city.name}, {pulse.city.country}",
        "date": pulse.timestamp[:10],
        "vitality_index": pulse.vitality_index,
        "evidence_coverage": pulse.evidence_coverage,
        "measured_share": pulse.measured_share,
        "headline_verifiable": pulse.headline_verifiable,
        "pillars": {k: p.score for k, p in pulse.pillars.items()},
        "components": {
            k: {"score": c.score, "measured_share": c.measured_share, "curated_key_facts": c.key_facts}
            for k, c in pulse.components.items()
        },
        "values": {k: v.score for k, v in pulse.values.items()},
        "integrity_flags": [{"severity": f.severity, "code": f.code, "message": f.message} for f in pulse.integrity_flags if f.severity != "info"],
    }
    return (
        "<summary>\n" + json.dumps(summary, indent=2, ensure_ascii=False) + "\n</summary>\n\n"
        "<evidence_ledger>\n" + json.dumps(ledger, indent=2, ensure_ascii=False) + "\n</evidence_ledger>"
    )


IMAGE_TASK = """Write BRAND IMAGE: how the city is experienced and perceived right now — \
the lived, daily reality a visitor or resident would recognize, grounded in today's \
measured signals (air, mobility, arrivals, attention, public mood). 120-200 words."""

POSITIONING_IDENTITY_TASK = """Write two narratives.

1. BRAND POSITIONING (150-250 words): where the city stands relative to peers on the \
democratic, participatory and innovative values, using the values scores, \
institutional-quality and participation entries, and any benchmarks. Be explicit about \
national proxies and self-assessments.

2. BRAND IDENTITY (2-3 sentences): the city's distinct civic character as the evidence \
supports it."""


class BrandNarrator:
    def __init__(self) -> None:
        self.api_key = credential("ANTHROPIC_API_KEY")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _call(self, pulse: CityBrandPulse, ledger: Dict[str, dict], task: str, fields: List[str]) -> Optional[dict]:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": _schema(fields)}},
            # Re-run on a fallback model if a safety classifier declines.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": f"{_data_block(pulse, ledger)}\n\n{task}"}],
        )
        if response.stop_reason == "refusal":
            logger.warning("Narrative request declined: %s", response.stop_details)
            return None
        text = next((b.text for b in response.content if b.type == "text"), None)
        return json.loads(text) if text else None

    @staticmethod
    def _build(kind: str, title: str, pillar: BrandingPillar, item: dict, ledger: Dict[str, dict]) -> BrandNarrative:
        cited = list(dict.fromkeys(item.get("cited_metrics", [])))
        unknown = [c for c in cited if c not in ledger]
        return BrandNarrative(
            narrative_type=kind,
            title=title,
            pillar=pillar,
            text=item["text"],
            status="generated",
            generated_at=utc_now_iso(),
            cited_metrics=[c for c in cited if c in ledger],
            uncited_claims_warning=[f"cited unknown evidence id: {c}" for c in unknown]
            or ([] if cited else ["narrative cites no evidence"]),
        )

    def brand_image(self, pulse: CityBrandPulse) -> Optional[BrandNarrative]:
        ledger = evidence_ledger(pulse)
        if not self.enabled or not ledger:
            return None
        result = self._call(pulse, ledger, IMAGE_TASK, ["brand_image"])
        if not result:
            return None
        return self._build("brand_image", f"{pulse.city.name} today", BrandingPillar.IMAGE, result["brand_image"], ledger)

    def positioning_and_identity(self, pulse: CityBrandPulse) -> Dict[str, BrandNarrative]:
        ledger = evidence_ledger(pulse)
        if not self.enabled or not ledger:
            return {}
        result = self._call(pulse, ledger, POSITIONING_IDENTITY_TASK, ["brand_positioning", "brand_identity"])
        if not result:
            return {}
        return {
            "brand_positioning": self._build("brand_positioning", f"{pulse.city.name} among its peers",
                                             BrandingPillar.POSITIONING, result["brand_positioning"], ledger),
            "brand_identity": self._build("brand_identity", f"The civic character of {pulse.city.name}",
                                          BrandingPillar.IDENTITY, result["brand_identity"], ledger),
        }


def slow_evidence_fingerprint(pulse: CityBrandPulse) -> Dict[str, str]:
    """Identifies the slow-moving evidence behind positioning/identity.

    Curated assessments, published benchmarks and national-proxy annual
    indicators change rarely; when none of them changed, the cached
    positioning/identity narratives are still valid.
    """
    fingerprint = {}
    for component in pulse.components.values():
        for m in component.metrics:
            if m.evidence_type != EvidenceType.MEASURED or m.geo_level == GeoLevel.NATIONAL_PROXY:
                fingerprint[f"{component.component.value}.{m.name}"] = f"{m.display_name}|{m.raw_value}"
    return dict(sorted(fingerprint.items()))
