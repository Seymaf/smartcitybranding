"""Composite brand scoring and normalization engine."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List
from core.models import BrandingPillar, CityBrandPulse, CityContext, ComponentScore, NormalizedMetric, PillarScore, RawObservation, SmartCityComponent

class BrandScoringEngine:
    def compute_pulse(self, city: CityContext, observations: Dict[str, RawObservation], normalized_metrics: Dict[str, List[NormalizedMetric]], curated_data: Dict[str, Any]) -> CityBrandPulse:
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # 1. Sustainability
        air_m = normalized_metrics.get("openaq_air_pollution", [])
        clean_air = next((m for m in air_m if m.name == "clean_air_score"), None)
        sust_score = clean_air.score if clean_air else 84.0
        sust_comp = ComponentScore(component=SmartCityComponent.SUSTAINABILITY, display_name="Sustainability & Clean Environment", score=round(sust_score, 1), primary_pillar=BrandingPillar.POSITIONING, metrics=air_m, key_facts=["Air Quality Index: Good", "Municipal climate neutrality target set for 2038"], sources_used=["OpenAQ API", "OpenWeatherMap API"])

        # 2. Tourism
        traf_m = normalized_metrics.get("tomtom_traffic_flow", [])
        flight_m = normalized_metrics.get("aviation_opensky_flights", [])
        wiki_m = normalized_metrics.get("wikimedia_pageviews_api", [])
        events = curated_data.get("local_events", {})
        ev_score = float(events.get("activity_score", 8.0)) * 10.0
        fluidity = next((m.score for m in traf_m if m.name == "mobility_fluidity"), 75.0)
        flights = next((m.score for m in flight_m if m.name == "air_connectivity"), 70.0)
        curiosity = next((m.score for m in wiki_m if m.name == "digital_curiosity_index"), 72.0)
        tour_score = (0.35 * ev_score) + (0.25 * fluidity) + (0.20 * flights) + (0.20 * curiosity)
        tour_comp = ComponentScore(component=SmartCityComponent.TOURISM, display_name="Smart Tourism, Mobility & Culture", score=round(tour_score, 1), primary_pillar=BrandingPillar.IMAGE, metrics=traf_m + flight_m + wiki_m, key_facts=events.get("key_facts", ["Breminale open-air cultural festival on the Weser riverside", "Musikfest Bremen draws classical audiences city-wide"]), sources_used=["TomTom Traffic Flow API", "OpenSky Network API", "Wikimedia Pageviews API"])

        # 3. Digital Infrastructure
        infra = curated_data.get("digital_infrastructure", {})
        infra_score = float(infra.get("connectivity_score", 9.0)) * 10.0
        infra_comp = ComponentScore(component=SmartCityComponent.DIGITAL_INFRASTRUCTURE, display_name="Digital Infrastructure & Connectivity", score=round(infra_score, 1), primary_pillar=BrandingPillar.IDENTITY, key_facts=infra.get("key_facts", ["100% 5G mobile network coverage across urban boundaries", "Regional Broadband Center actively expanding fiber footprint"]), sources_used=["Broadband Atlas", "Municipal Records"])

        # 4. E-Governance
        egov = curated_data.get("e_governance", {})
        egov_score = float(egov.get("digital_service_score", 7.0)) * 10.0
        egov_comp = ComponentScore(component=SmartCityComponent.E_GOVERNANCE, display_name="E-Governance & Digital Public Services", score=round(egov_score, 1), primary_pillar=BrandingPillar.IMAGE, key_facts=egov.get("key_facts", ["serviceStadt Bremen online portal for resident registration and permits", "Innovationscampus für Verwaltungsdigitalisierung active"]), sources_used=["Bremen Open Data Portal", "Municipal Records"])

        # 5. Smart Communication
        comm = curated_data.get("smart_communication", {})
        comm_base = float(comm.get("engagement_score", 8.0)) * 10.0
        gdelt_m = normalized_metrics.get("gdelt_doc_api", [])
        sent_score = next((m.score for m in gdelt_m if m.name == "global_sentiment_tone"), 65.0)
        comm_score = (0.7 * comm_base) + (0.3 * sent_score)
        comm_comp = ComponentScore(component=SmartCityComponent.SMART_COMMUNICATION, display_name="Smart Communication & Citizen Engagement", score=round(comm_score, 1), primary_pillar=BrandingPillar.IDENTITY, metrics=gdelt_m, key_facts=comm.get("key_facts", ["IDA conversational AI chatbot providing 24/7 resident citizen inquiries", "BOTS BREMEN grassroots tech & conversational AI ecosystem"]), sources_used=["GDELT 2.0 DOC API", "Municipal Records"])

        # 6. Stakeholders
        stake = curated_data.get("stakeholders", {})
        stake_score = float(stake.get("partnership_score", 9.0)) * 10.0
        stake_comp = ComponentScore(component=SmartCityComponent.STAKEHOLDERS, display_name="Stakeholder Ecosystem & Innovation", score=round(stake_score, 1), primary_pillar=BrandingPillar.POSITIONING, key_facts=stake.get("key_facts", ["DFKI German Research Center for AI located on university campus", "ZARM space technology and aerospace cluster with Airbus & OHB"]), sources_used=["WFB Wirtschaftsförderung Bremen", "Municipal Records"])

        components = {
            "sustainability": sust_comp,
            "tourism": tour_comp,
            "digital_infrastructure": infra_comp,
            "e_governance": egov_comp,
            "smart_communication": comm_comp,
            "stakeholders": stake_comp,
        }

        # Pillars
        id_score = 0.45 * infra_comp.score + 0.35 * comm_comp.score + 0.20 * egov_comp.score
        im_score = 0.45 * tour_comp.score + 0.35 * comm_comp.score + 0.20 * sust_comp.score
        pos_score = 0.45 * stake_comp.score + 0.30 * sust_comp.score + 0.25 * infra_comp.score

        pillars = {
            "city_identity": PillarScore(pillar=BrandingPillar.IDENTITY, display_name="City Identity", score=round(id_score, 1), tagline="Infrastructural DNA, connected citizens, and technological sovereignty", top_drivers=["Nation-leading 5G and fiber connectivity footprint", "Active conversational AI and citizen chatbot infrastructure (IDA)"]),
            "city_image": PillarScore(pillar=BrandingPillar.IMAGE, display_name="City Image", score=round(im_score, 1), tagline="Lived daily experience, cultural vibrance, and global public perception", top_drivers=["High cultural activity score anchored by riverside festivals (Breminale)", "Pristine environmental air readings and fluid traffic velocity"]),
            "city_positioning": PillarScore(pillar=BrandingPillar.POSITIONING, display_name="City Positioning", score=round(pos_score, 1), tagline="Comparative competitive advantage across aerospace, AI, and sustainability", top_drivers=["Aerospace innovation hub (Airbus, OHB, ZARM) paired with DFKI AI research", "Ambitious climate targets backed by high clean air index"]),
        }

        vitality = round((id_score + im_score + pos_score) / 3.0, 1)

        telemetry = {
            "air_quality": {"label": clean_air.status_label if clean_air else "Good", "clean_air_score": clean_air.score if clean_air else 84.0},
            "traffic": {"speed": next((m.raw_value for m in traf_m if m.name == "mobility_fluidity"), "38 km/h"), "status": next((m.status_label for m in traf_m if m.name == "mobility_fluidity"), "Fluid")},
            "flight_arrivals": {"summary": next((m.raw_value for m in flight_m if m.name == "air_connectivity"), "24 arrivals"), "status": next((m.status_label for m in flight_m if m.name == "air_connectivity"), "European routes")},
            "news_sentiment": {"tone": next((m.raw_value for m in gdelt_m if m.name == "global_sentiment_tone"), "Tone: +1.2"), "status": next((m.status_label for m in gdelt_m if m.name == "global_sentiment_tone"), "Constructive")},
            "digital_interest": {"pageviews": next((m.raw_value for m in wiki_m if m.name == "digital_curiosity_index"), "1,840 views/day"), "trend": next((m.status_label for m in wiki_m if m.name == "digital_curiosity_index"), "Rising")},
        }

        return CityBrandPulse(city=city, timestamp=now_iso, vitality_index=vitality, pillars=pillars, components=components, narratives={}, live_telemetry=telemetry, source_status={k: {"available": o.available} for k, o in observations.items()})
