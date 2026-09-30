"""Core domain models and schemas for the Smart City Branding platform."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

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

@dataclass
class CityContext:
    city_id: str = "bremen"
    name: str = "Bremen"
    country: str = "Germany"
    country_code: str = "DE"
    latitude: float = 53.0793
    longitude: float = 8.8017
    airport_iata: str = "BRE"
    timezone: str = "Europe/Berlin"
    wikipedia_title: str = "Bremen"
    gdelt_query: str = "Bremen Germany"

@dataclass
class RawObservation:
    source_id: str
    component: SmartCityComponent
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    available: bool = True
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NormalizedMetric:
    name: str
    display_name: str
    raw_value: Any
    unit: str
    score: float
    weight: float = 1.0
    status_label: str = "Normal"

@dataclass
class ComponentScore:
    component: SmartCityComponent
    display_name: str
    score: float
    primary_pillar: BrandingPillar
    metrics: List[NormalizedMetric] = field(default_factory=list)
    key_facts: List[str] = field(default_factory=list)
    sources_used: List[str] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class PillarScore:
    pillar: BrandingPillar
    display_name: str
    score: float
    tagline: str
    contributing_components: List[str] = field(default_factory=list)
    top_drivers: List[str] = field(default_factory=list)

@dataclass
class BrandNarrative:
    narrative_type: str
    title: str
    pillar: BrandingPillar
    text: str
    status: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    grounding_signals: List[str] = field(default_factory=list)

@dataclass
class CityBrandPulse:
    city: CityContext
    timestamp: str
    vitality_index: float
    pillars: Dict[str, PillarScore]
    components: Dict[str, ComponentScore]
    narratives: Dict[str, BrandNarrative]
    live_telemetry: Dict[str, Any]
    source_status: Dict[str, Dict[str, Any]]
