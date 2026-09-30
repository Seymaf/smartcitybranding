"""Master orchestrator combining connectors, scoring engine, and narrative generation."""
from __future__ import annotations
import json
from datetime import date, datetime, timezone
from typing import Any, Dict, List
from connectors.base import BaseConnector
from connectors.communication.gdelt import GDELTNewsConnector
from connectors.communication.wikimedia import WikimediaPageviewsConnector
from connectors.curated.manual_data import CuratedDataConnector
from connectors.sustainability.air_quality import AirQualityConnector
from connectors.tourism.flights import FlightsConnector
from connectors.tourism.traffic import TrafficConnector
from core.config import ARCHIVE_DIR, load_manual_data
from core.models import CityBrandPulse, CityContext, NormalizedMetric, RawObservation
from engine.brand_narrator import BrandNarrator
from engine.scoring import BrandScoringEngine

class CityBrandOrchestrator:
    def __init__(self, city: CityContext = None) -> None:
        self.city = city or CityContext()
        self.connectors: List[BaseConnector] = [
            AirQualityConnector(),
            TrafficConnector(),
            FlightsConnector(),
            GDELTNewsConnector(),
            WikimediaPageviewsConnector(),
            CuratedDataConnector(),
        ]
        self.scoring_engine = BrandScoringEngine()
        self.narrator = BrandNarrator()

    def run_pipeline(self, force_refresh: bool = False) -> CityBrandPulse:
        observations = {}
        normalized_metrics = {}
        for connector in self.connectors:
            try:
                obs = connector.fetch(self.city)
                m = connector.normalize(obs)
            except Exception as exc:
                obs = connector.fallback(self.city, exc)
                m = connector.normalize(obs)
            observations[connector.source_id] = obs
            normalized_metrics[connector.source_id] = m

        try:
            curated = load_manual_data()
        except Exception:
            curated = {}

        pulse = self.scoring_engine.compute_pulse(city=self.city, observations=observations, normalized_metrics=normalized_metrics, curated_data=curated)
        pulse.narratives = self.narrator.generate_narratives(pulse, force_refresh=force_refresh)
        return pulse
