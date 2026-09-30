"""Core domain models for the Smart City Branding platform.

Every number the platform reports is a `NormalizedMetric` carrying its own
provenance (which source, which URL, when it was retrieved, whether it was
measured live, curated by hand, or taken from a published benchmark, and at
which geographic level). That provenance is what lets the platform show a
city's brand value *without* greenwashing: a claim can always be traced back
to the evidence behind it, and a missing source is reported as missing
instead of being papered over with an estimate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SmartCityComponent(str, Enum):
    SUSTAINABILITY = "sustainability"
    TOURISM = "tourism"
    DIGITAL_INFRASTRUCTURE = "digital_infrastructure"
    E_GOVERNANCE = "e_governance"
    SMART_COMMUNICATION = "smart_communication"
    STAKEHOLDERS = "stakeholders"


class BrandingPillar(str, Enum):
    IDENTITY = "city_identity"
    IMAGE = "city_image"
    POSITIONING = "city_positioning"


class ValueDimension(str, Enum):
    """The civic values the company's mission is about."""

    DEMOCRATIC = "democratic"
    PARTICIPATORY = "participatory"
    INNOVATIVE = "innovative"


class EvidenceType(str, Enum):
    MEASURED = "measured"  # fetched live from an API on this run
    BENCHMARK = "benchmark"  # published index/ranking, entered with a citation
    CURATED = "curated"  # hand-maintained assessment in manual_data.json


class GeoLevel(str, Enum):
    CITY = "city"
    REGIONAL = "regional"
    NATIONAL_PROXY = "national_proxy"


class UpdateCadence(str, Enum):
    STREAMING = "streaming"
    INTRA_HOUR = "intra_hour"
    DAILY = "daily"
    WEEKLY = "weekly"
    PERIODIC_BENCHMARK = "benchmark"
    MANUAL_CURATED = "manual_curated"


class AccessTier(str, Enum):
    FREE_OPEN = "free_open"
    FREEMIUM = "freemium"
    SELF_HOSTED = "self_hosted"
    PAID_ENTERPRISE = "paid_enterprise"


class SourceStatus(str, Enum):
    OK = "ok"
    NOT_CONFIGURED = "not_configured"  # API key / city endpoint missing
    ERROR = "error"  # request or parsing failed
    NO_DATA = "no_data"  # request succeeded but returned nothing usable


@dataclass
class CityContext:
    """Everything a connector needs to know about the city it queries.

    City-specific endpoints (open-data portal, participation platform,
    Open311 server) are optional; connectors that need one report
    `not_configured` when it's absent.
    """

    city_id: str = "bremen"
    name: str = "Bremen"
    country: str = "Germany"
    country_code: str = "DE"
    country_iso3: str = "DEU"
    latitude: float = 53.0793
    longitude: float = 8.8017
    airport_iata: str = "BRE"
    airport_icao: str = "EDDW"
    timezone: str = "Europe/Berlin"
    wikipedia_project: str = "en.wikipedia"
    wikipedia_title: str = "Bremen"
    news_query: str = '"Bremen"'
    reddit_query: str = "Bremen"
    places_query: str = "tourist attractions in Bremen"
    adzuna_country: str = "de"
    ckan_api_url: Optional[str] = "https://www.govdata.de/ckan/api/3/action"
    ckan_query: str = "Bremen"
    data_europa_query: str = "Bremen"
    decidim_api_url: Optional[str] = None
    open311_url: Optional[str] = None
    open311_jurisdiction_id: Optional[str] = None


@dataclass
class NormalizedMetric:
    name: str
    display_name: str
    raw_value: Any
    unit: str
    score: float  # 0-100
    source_id: str
    source_url: str
    component: Optional[SmartCityComponent] = None
    evidence_type: EvidenceType = EvidenceType.MEASURED
    geo_level: GeoLevel = GeoLevel.CITY
    retrieved_at: str = field(default_factory=utc_now_iso)
    weight: float = 1.0
    values: List[ValueDimension] = field(default_factory=list)
    note: str = ""


@dataclass
class RawObservation:
    source_id: str
    component: SmartCityComponent
    status: SourceStatus = SourceStatus.OK
    timestamp: str = field(default_factory=utc_now_iso)
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def available(self) -> bool:
        return self.status == SourceStatus.OK


@dataclass
class SourceReport:
    source_id: str
    name: str
    component: SmartCityComponent
    status: SourceStatus
    link: str
    access_tier: AccessTier
    metrics: int = 0
    error: Optional[str] = None


@dataclass
class ComponentScore:
    component: SmartCityComponent
    display_name: str
    score: Optional[float]  # None when no evidence exists at all
    primary_pillar: BrandingPillar
    metrics: List[NormalizedMetric] = field(default_factory=list)
    measured_share: float = 0.0  # share of total weight that is live-measured
    key_facts: List[str] = field(default_factory=list)


@dataclass
class PillarScore:
    pillar: BrandingPillar
    display_name: str
    score: Optional[float]
    contributing_components: List[str] = field(default_factory=list)


@dataclass
class ValueScore:
    dimension: ValueDimension
    score: Optional[float]
    metrics: List[str] = field(default_factory=list)


@dataclass
class IntegrityFlag:
    severity: str  # "info" | "warning" | "critical"
    code: str
    message: str
    component: Optional[str] = None


@dataclass
class BrandNarrative:
    narrative_type: str
    title: str
    pillar: BrandingPillar
    text: str
    status: str  # "generated", "cached", "not_generated"
    generated_at: str = field(default_factory=utc_now_iso)
    cited_metrics: List[str] = field(default_factory=list)
    uncited_claims_warning: List[str] = field(default_factory=list)


@dataclass
class CityBrandPulse:
    city: CityContext
    timestamp: str
    vitality_index: Optional[float]
    evidence_coverage: float  # share of expected sources that returned data
    measured_share: float  # share of all evidence weight that is live-measured
    headline_verifiable: bool  # False when too little live evidence backs the index
    pillars: Dict[str, PillarScore]
    components: Dict[str, ComponentScore]
    values: Dict[str, ValueScore]
    integrity_flags: List[IntegrityFlag]
    sources: List[SourceReport]
    narratives: Dict[str, BrandNarrative] = field(default_factory=dict)
