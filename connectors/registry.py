"""All connectors the pipeline runs, grouped by smart city component.

See METHODOLOGY.md for the source-map rows that are intentionally not
implemented (paid, partnership-only, or bulk-download datasets).
"""
from __future__ import annotations

from typing import List

from connectors.base import BaseConnector
from connectors.communication.gdelt import GDELTNewsConnector
from connectors.communication.open311 import Open311Connector
from connectors.communication.reddit import RedditConnector
from connectors.curated.benchmarks import BenchmarksConnector
from connectors.curated.manual_data import CuratedDataConnector
from connectors.digital.opencellid import OpenCelliDConnector
from connectors.digital.peeringdb import PeeringDBConnector
from connectors.digital.tomtom import TomTomTrafficConnector
from connectors.governance.ckan import CKANOpenDataConnector
from connectors.governance.data_europa import DataEuropaConnector
from connectors.governance.decidim import DecidimConnector
from connectors.governance.world_bank_wgi import WorldBankGovernanceConnector
from connectors.stakeholders.adzuna import AdzunaConnector
from connectors.stakeholders.world_bank_fdi import WorldBankFDIConnector
from connectors.sustainability.aqicn import AQICNConnector
from connectors.sustainability.openaq import OpenAQConnector
from connectors.sustainability.openweather import OpenWeatherAirConnector
from connectors.tourism.aviationstack import AviationStackConnector
from connectors.tourism.google_places import GooglePlacesConnector
from connectors.tourism.opensky import OpenSkyConnector
from connectors.tourism.wikimedia import WikimediaPageviewsConnector


def default_connectors() -> List[BaseConnector]:
    return [
        # Smart Communication
        GDELTNewsConnector(),
        RedditConnector(),
        Open311Connector(),
        # E-Governance
        WorldBankGovernanceConnector(),
        CKANOpenDataConnector(),
        DataEuropaConnector(),
        DecidimConnector(),
        # Stakeholders
        AdzunaConnector(),
        WorldBankFDIConnector(),
        # Smart Tourism
        AviationStackConnector(),
        OpenSkyConnector(),
        WikimediaPageviewsConnector(),
        GooglePlacesConnector(),
        # Digital Infrastructure
        TomTomTrafficConnector(),
        PeeringDBConnector(),
        OpenCelliDConnector(),
        # Sustainability
        OpenWeatherAirConnector(),
        OpenAQConnector(),
        AQICNConnector(),
        # Curated + published benchmarks (all components)
        CuratedDataConnector(),
        BenchmarksConnector(),
    ]
