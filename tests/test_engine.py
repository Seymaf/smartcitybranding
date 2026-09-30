"""Scoring, integrity checks, narrator grounding and archiving."""
from __future__ import annotations

import json
from types import SimpleNamespace

from connectors.base import BaseConnector
from core.models import (
    CityContext,
    EvidenceType,
    GeoLevel,
    NormalizedMetric,
    RawObservation,
    SmartCityComponent,
    SourceReport,
    SourceStatus,
    AccessTier,
    ValueDimension,
)
from engine import brand_narrator, orchestrator
from engine.brand_narrator import BrandNarrator, evidence_ledger
from engine.orchestrator import CityBrandOrchestrator, save_archive
from engine.scoring import BrandScoringEngine

CITY = CityContext()


def metric(component, score, evidence=EvidenceType.MEASURED, geo=GeoLevel.CITY, weight=1.0, values=(), name=None):
    return NormalizedMetric(
        name=name or f"m_{component.value}_{score}_{evidence.value}", display_name="x", raw_value=score, unit="u",
        score=score, source_id="s", source_url="u", component=component, evidence_type=evidence, geo_level=geo,
        weight=weight, values=list(values),
    )


def source(status=SourceStatus.OK):
    return SourceReport("s", "S", SmartCityComponent.TOURISM, status, "u", AccessTier.FREE_OPEN)


def codes(pulse):
    return {f.code for f in pulse.integrity_flags}


def test_component_without_evidence_has_no_score():
    pulse = BrandScoringEngine().compute_pulse(CITY, [metric(SmartCityComponent.TOURISM, 80)], [source()], {})
    assert pulse.components["sustainability"].score is None
    assert pulse.components["tourism"].score == 80.0
    assert "NO_EVIDENCE" in codes(pulse)
    assert any(f.severity == "critical" and f.component == "sustainability" for f in pulse.integrity_flags)


def test_weights_favour_measured_over_curated_and_national_proxies():
    engine = BrandScoringEngine()
    ms = [
        metric(SmartCityComponent.E_GOVERNANCE, 100, evidence=EvidenceType.CURATED, weight=0.5),
        metric(SmartCityComponent.E_GOVERNANCE, 40),
        metric(SmartCityComponent.E_GOVERNANCE, 70, geo=GeoLevel.NATIONAL_PROXY),
    ]
    pulse = engine.compute_pulse(CITY, ms, [source()], {})
    egov = pulse.components["e_governance"]
    # weights 0.5, 1.0, 0.5 -> (50 + 40 + 35) / 2
    assert egov.score == 62.5
    assert egov.measured_share == 0.75


def test_curated_only_component_is_flagged_self_reported():
    pulse = BrandScoringEngine().compute_pulse(
        CITY, [metric(SmartCityComponent.STAKEHOLDERS, 90, evidence=EvidenceType.CURATED, weight=0.5)], [source()], {})
    assert "SELF_REPORTED_ONLY" in codes(pulse)


def test_self_assessment_far_above_evidence_is_flagged():
    ms = [metric(SmartCityComponent.SMART_COMMUNICATION, 90, evidence=EvidenceType.CURATED, weight=0.5),
          metric(SmartCityComponent.SMART_COMMUNICATION, 40)]
    pulse = BrandScoringEngine().compute_pulse(CITY, ms, [source()], {})
    assert "CURATED_ABOVE_EVIDENCE" in codes(pulse)


def test_poor_measured_air_quality_blocks_green_claims():
    pulse = BrandScoringEngine().compute_pulse(CITY, [metric(SmartCityComponent.SUSTAINABILITY, 30)], [source()], {})
    assert "SUSTAINABILITY_GAP" in codes(pulse)


def test_headline_requires_mostly_measured_evidence_and_all_pillars():
    engine = BrandScoringEngine()
    all_measured = [metric(c, 70) for c in SmartCityComponent]
    assert engine.compute_pulse(CITY, all_measured, [source()], {}).headline_verifiable
    curated_heavy = [metric(c, 90, evidence=EvidenceType.CURATED, weight=1.0) for c in SmartCityComponent] + [metric(SmartCityComponent.TOURISM, 60)]
    pulse = engine.compute_pulse(CITY, curated_heavy, [source()], {})
    assert not pulse.headline_verifiable and "HEADLINE_NOT_VERIFIABLE" in codes(pulse)


def test_values_lens_uses_only_tagged_metrics():
    ms = [metric(SmartCityComponent.E_GOVERNANCE, 80, values=(ValueDimension.DEMOCRATIC,)),
          metric(SmartCityComponent.TOURISM, 20)]
    pulse = BrandScoringEngine().compute_pulse(CITY, ms, [source()], {})
    assert pulse.values["democratic"].score == 80.0
    assert pulse.values["innovative"].score is None
    assert "VALUE_UNEVIDENCED" in codes(pulse)


# ---- narrator ----------------------------------------------------------------


def fake_anthropic(monkeypatch, payload, stop_reason="end_turn"):
    captured = {}

    class Messages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(stop_reason=stop_reason, stop_details=None,
                                   content=[SimpleNamespace(type="text", text=json.dumps(payload))])

    class Client:
        def __init__(self, api_key):
            self.beta = SimpleNamespace(messages=Messages())

    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", Client)
    return captured


def sample_pulse():
    ms = [metric(SmartCityComponent.SUSTAINABILITY, 80, name="owm_aqi"), metric(SmartCityComponent.TOURISM, 60, name="wiki_interest")]
    return BrandScoringEngine().compute_pulse(CITY, ms, [source()], {})


def test_narrator_disabled_without_key():
    narrator = BrandNarrator()
    assert not narrator.enabled
    assert narrator.brand_image(sample_pulse()) is None


def test_narrator_validates_citations(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    captured = fake_anthropic(monkeypatch, {"brand_image": {"text": "Clean air today.", "cited_metrics": ["sustainability.owm_aqi", "made.up"]}})
    narrative = BrandNarrator().brand_image(sample_pulse())
    assert narrative.cited_metrics == ["sustainability.owm_aqi"]
    assert narrative.uncited_claims_warning == ["cited unknown evidence id: made.up"]
    assert captured["model"] == "claude-opus-5-5"
    assert "sustainability.owm_aqi" in captured["messages"][0]["content"]
    assert captured["output_config"]["format"]["type"] == "json_schema"


def test_narrator_refusal_returns_nothing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    fake_anthropic(monkeypatch, {}, stop_reason="refusal")
    assert BrandNarrator().brand_image(sample_pulse()) is None


def test_ledger_ids_are_component_qualified():
    assert set(evidence_ledger(sample_pulse())) == {"sustainability.owm_aqi", "tourism.wiki_interest"}


# ---- orchestrator ------------------------------------------------------------


class StubConnector(BaseConnector):
    source_id = "stub"
    name = "Stub"
    component = SmartCityComponent.SUSTAINABILITY
    measurement_track = "Air Quality"
    link = "https://example.org"

    def fetch(self, city):
        return self.ok({"aqi": 1})

    def normalize(self, observation, city):
        return [self.metric("stub_aqi", "Stub AQI", 1, "AQI", 90)]


class BrokenConnector(StubConnector):
    source_id = "broken"

    def fetch(self, city):
        raise RuntimeError("boom")


def test_pipeline_survives_failures_and_archives(tmp_path, monkeypatch):
    monkeypatch.setattr(orchestrator, "ARCHIVE_DIR", tmp_path)
    pulse, raw = CityBrandOrchestrator(connectors=[StubConnector(), BrokenConnector()]).run_pipeline(with_narratives=False)
    assert pulse.components["sustainability"].score == 90.0
    assert {s.source_id: s.status for s in pulse.sources} == {"stub": SourceStatus.OK, "broken": SourceStatus.ERROR}
    path = save_archive(pulse, raw)
    saved = json.loads(path.read_text())
    assert saved["pulse"]["components"]["sustainability"]["score"] == 90.0
    assert saved["raw_observations"]["broken"]["status"] == "error"


def test_positioning_cache_reused_until_slow_evidence_changes(tmp_path, monkeypatch):
    from engine import narrative_cache
    monkeypatch.setattr(narrative_cache, "CACHE_PATH", tmp_path / "cache.json")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    calls = []

    def fake_call(self, pulse, ledger, task, fields):
        calls.append(fields)
        return {f: {"text": f, "cited_metrics": []} for f in fields}

    monkeypatch.setattr(brand_narrator.BrandNarrator, "_call", fake_call)
    orch = CityBrandOrchestrator(connectors=[StubConnector()])
    first, _ = orch.run_pipeline()
    second, _ = orch.run_pipeline()
    assert first.narratives["brand_positioning"].status == "generated"
    assert second.narratives["brand_positioning"].status == "cached"
    assert calls.count(["brand_positioning", "brand_identity"]) == 1
    assert calls.count(["brand_image"]) == 2


def test_claude_failure_keeps_the_evidence(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    def boom(self, pulse):
        raise RuntimeError("API down")

    monkeypatch.setattr(brand_narrator.BrandNarrator, "brand_image", boom)
    pulse, _ = CityBrandOrchestrator(connectors=[StubConnector()]).run_pipeline()
    assert pulse.narratives == {} and pulse.components["sustainability"].score == 90.0
