"""Generates Bremen's brand narratives using the Anthropic Claude API.

Takes the same air quality data (the city's "sustainability" smart city
component) and traffic data (its "tourism" component) that city_pulse.py
uses, and turns them into three distinct branding narratives — image,
positioning, and identity — instead of a single daily summary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import anthropic

from config import ANTHROPIC_API_KEY

SYSTEM_PROMPT = """You are a city branding strategist for Bremen, Germany. You \
translate real-time civic data into brand storytelling for two smart city \
components: sustainability (air quality) and tourism (traffic flow). You use \
that data as evidence for how the city feels right now, how it compares to \
peer cities, and what makes it distinct. You never invent facts the data \
doesn't support, but you're skilled at reading the human story behind the \
numbers."""

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


def _build_user_prompt(air_quality: dict[str, Any], traffic: dict[str, Any]) -> str:
    today = datetime.now().strftime("%A, %d %B %Y")
    return f"""Today is {today}.

Here is today's smart city data for Bremen:

Sustainability component — Air Quality (OpenWeatherMap, measured {air_quality.get('measured_at')}):
- AQI index: {air_quality.get('aqi')} ({air_quality.get('aqi_label')})
- PM2.5: {air_quality.get('pm2_5')} µg/m³
- PM10: {air_quality.get('pm10')} µg/m³
- NO2: {air_quality.get('no2')} µg/m³
- O3: {air_quality.get('o3')} µg/m³
- SO2: {air_quality.get('so2')} µg/m³
- CO: {air_quality.get('co')} µg/m³

Tourism component — Traffic (TomTom, city center):
- Current average speed: {traffic.get('current_speed_kmh')} km/h
- Free-flow speed: {traffic.get('free_flow_speed_kmh')} km/h
- Congestion ratio: {traffic.get('congestion_ratio')}
- Road closure reported: {traffic.get('road_closure')}
- Confidence score: {traffic.get('confidence')}

Using this data, write three separate brand narratives for Bremen:

1. BRAND IMAGE — An emotional, sensory description of what it's like to \
experience the city right now. Make the reader feel the air, the pace of \
the streets, the mood of the day.

2. BRAND POSITIONING — A narrative on how this data suggests Bremen compares \
to peer cities in innovation and livability. Frame it as a case for why \
Bremen stands out, not a dry statistical comparison.

3. BRAND IDENTITY — A short statement (2-3 sentences) capturing Bremen's \
distinct character today, grounded in this data.

Each narrative should be self-contained — a reader should be able to read \
just one of the three and get a complete, satisfying piece of writing."""


def generate_brand_narratives(
    air_quality: dict[str, Any], traffic: dict[str, Any]
) -> BrandNarratives:
    """Sends sustainability + tourism data to Claude and returns three brand narratives."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
        messages=[
            {"role": "user", "content": _build_user_prompt(air_quality, traffic)}
        ],
    )

    text = next(block.text for block in message.content if block.type == "text")
    data = json.loads(text)

    return BrandNarratives(
        image=data["brand_image"],
        positioning=data["brand_positioning"],
        identity=data["brand_identity"],
    )
