"""Generates Bremen's brand narratives using the Anthropic Claude API.

Takes data from all six smart city components — sustainability (air
quality), tourism (traffic), digital infrastructure, e-governance, smart
communication, and stakeholders — plus a real-time flight arrivals signal
(who is actually visiting right now, enriching the tourism component) — and
turns all of it into three distinct branding narratives: image,
positioning, and identity.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import anthropic

from config import ANTHROPIC_API_KEY

SYSTEM_PROMPT = """You are a city branding strategist for Bremen, Germany. You \
translate real-time and curated civic data into brand storytelling across six \
smart city components: sustainability (air quality), tourism (traffic flow, \
enriched by real-time flight arrival data showing who is actually visiting \
right now), digital infrastructure, e-governance, smart communication, and \
the local stakeholder ecosystem. You weave together whichever signals are \
strongest — some days the story is environmental, other days it's about \
connectivity, civic innovation, or who's landing at the airport today — to \
explain how the city feels right now, how it compares to peer cities, and \
what makes it distinct. You never invent facts the data doesn't support, but \
you're skilled at reading the human story behind the numbers. When flight \
arrival data is unavailable, simply don't reference it — never mention the \
outage or apologize for missing data."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "brand_image": {
            "type": "string",
            "description": (
                "An emotional, sensory description of what it feels like to "
                "experience Bremen right now, grounded in today's data."
            ),
        },
        "brand_positioning": {
            "type": "string",
            "description": (
                "A narrative on how today's data suggests Bremen compares to "
                "peer cities in innovation and livability."
            ),
        },
        "brand_identity": {
            "type": "string",
            "description": (
                "A short statement capturing Bremen's distinct character, "
                "grounded in today's data."
            ),
        },
    },
    "required": ["brand_image", "brand_positioning", "brand_identity"],
    "additionalProperties": False,
}


@dataclass
class BrandNarratives:
    image: str
    positioning: str
    identity: str


def _format_manual_section(label: str, data: dict[str, Any]) -> str:
    """Formats one manually maintained component as text.

    Each component uses its own score field name (e.g. "connectivity_score",
    "partnership_score") rather than a uniform "score" key, so this treats
    every key other than key_facts/last_updated/note as a metric to display.
    """
    metric_keys = [key for key in data if key not in ("key_facts", "last_updated", "note")]
    metric_lines = [
        f"- {key.replace('_', ' ').capitalize()}: {data[key]}/10" for key in metric_keys
    ]

    facts = data.get("key_facts", [])
    facts_block = (
        "\n".join(f"  - {fact}" for fact in facts)
        if facts
        else "  - (no key facts provided)"
    )

    lines = [
        f"{label} component (manual data, last updated {data.get('last_updated')}):",
        *metric_lines,
        "- Key facts:",
        facts_block,
    ]
    if "note" in data:
        lines.append(f"- Note: {data['note']}")

    return "\n".join(lines)


def _format_flight_arrivals(data: dict[str, Any]) -> str | None:
    """Formats the flight arrivals signal as text, or None if unavailable.

    Returning None lets the caller drop this section entirely when the data
    isn't available, instead of feeding Claude a paragraph about an API
    outage that has nothing to do with Bremen's brand.
    """
    if not data.get("available"):
        return None

    patterns = data.get("notable_patterns") or []
    patterns_block = (
        "\n".join(f"  - {p}" for p in patterns)
        if patterns
        else "  - (no notable patterns)"
    )
    origins = ", ".join(data.get("origins", [])) or "none recorded"

    return (
        f"Tourism component (continued) — Flight Arrivals at Bremen Airport "
        f"(AviationStack, real-time, as of {data.get('fetched_at')}):\n"
        f"- Total arrivals today: {data.get('total_arrivals')}\n"
        f"- Origin countries/cities represented: {origins}\n"
        f"- Notable patterns:\n{patterns_block}"
    )


def _build_user_prompt(
    air_quality: dict[str, Any],
    traffic: dict[str, Any],
    flight_arrivals: dict[str, Any],
    digital_infrastructure: dict[str, Any],
    e_governance: dict[str, Any],
    smart_communication: dict[str, Any],
    stakeholders: dict[str, Any],
) -> str:
    today = datetime.now().strftime("%A, %d %B %Y")

    sections = [
        f"""Sustainability component — Air Quality (OpenWeatherMap, measured {air_quality.get('measured_at')}):
- AQI index: {air_quality.get('aqi')} ({air_quality.get('aqi_label')})
- PM2.5: {air_quality.get('pm2_5')} µg/m³
- PM10: {air_quality.get('pm10')} µg/m³
- NO2: {air_quality.get('no2')} µg/m³
- O3: {air_quality.get('o3')} µg/m³
- SO2: {air_quality.get('so2')} µg/m³
- CO: {air_quality.get('co')} µg/m³""",
        f"""Tourism component — Traffic (TomTom, city center):
- Current average speed: {traffic.get('current_speed_kmh')} km/h
- Free-flow speed: {traffic.get('free_flow_speed_kmh')} km/h
- Congestion ratio: {traffic.get('congestion_ratio')}
- Road closure reported: {traffic.get('road_closure')}
- Confidence score: {traffic.get('confidence')}""",
        _format_flight_arrivals(flight_arrivals),
        _format_manual_section("Digital Infrastructure", digital_infrastructure),
        _format_manual_section("E-Governance", e_governance),
        _format_manual_section("Smart Communication", smart_communication),
        _format_manual_section("Stakeholders", stakeholders),
    ]
    data_block = "\n\n".join(section for section in sections if section is not None)

    return f"""Today is {today}.

Here is today's smart city data for Bremen, across all six components:

{data_block}

Using this data, write three separate brand narratives for Bremen. Draw on \
whichever components are most relevant to each narrative — you don't need to \
mention all six in every narrative, but each narrative should be grounded in \
specific data points, not generic city-branding language. Where a component \
carries a "Note" flagging it as estimated or provisional, treat it with \
appropriately less certainty than the verified components — don't present it \
as a confirmed fact.

1. BRAND IMAGE — An emotional, sensory description of what it's like to \
experience the city right now. Make the reader feel the air, the pace of \
the streets, the mood of the day.

2. BRAND POSITIONING — A narrative on how this data suggests Bremen compares \
to peer cities in innovation and livability. Frame it as a case for why \
Bremen stands out, not a dry statistical comparison. If flight arrival data \
is present, it's especially useful here — who is actually flying in today is \
concrete evidence of Bremen's international pull, stronger than an abstract \
claim about tourism appeal.

3. BRAND IDENTITY — A short statement (2-3 sentences) capturing Bremen's \
distinct character today, grounded in this data.

Each narrative should be self-contained — a reader should be able to read \
just one of the three and get a complete, satisfying piece of writing."""


def generate_brand_narratives(
    air_quality: dict[str, Any],
    traffic: dict[str, Any],
    flight_arrivals: dict[str, Any],
    digital_infrastructure: dict[str, Any],
    e_governance: dict[str, Any],
    smart_communication: dict[str, Any],
    stakeholders: dict[str, Any],
) -> BrandNarratives:
    """Sends all seven inputs to Claude and returns three brand narratives."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    user_prompt = _build_user_prompt(
        air_quality=air_quality,
        traffic=traffic,
        flight_arrivals=flight_arrivals,
        digital_infrastructure=digital_infrastructure,
        e_governance=e_governance,
        smart_communication=smart_communication,
        stakeholders=stakeholders,
    )

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = next(block.text for block in message.content if block.type == "text")
    data = json.loads(text)

    return BrandNarratives(
        image=data["brand_image"],
        positioning=data["brand_positioning"],
        identity=data["brand_identity"],
    )
