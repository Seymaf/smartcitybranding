"""Generates Bremen's daily 'city pulse' summary using the Anthropic Claude API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import anthropic

from config import ANTHROPIC_API_KEY

SYSTEM_PROMPT = """You are the voice behind "Bremen City Pulse," a short daily \
briefing published for residents and visitors of Bremen, Germany. Your tone is \
warm, welcoming, and proud of the city — the kind of writing a tourism board \
would be happy to publish — but you never sacrifice accuracy for charm. You \
always ground the summary in the real data you're given, translating raw \
numbers into what they actually mean for someone's day (a walk along the \
Weser, a bike ride through the Altstadt, a stroll to the Marktplatz)."""


def _build_user_prompt(air_quality: dict[str, Any], traffic: dict[str, Any]) -> str:
    today = datetime.now().strftime("%A, %d %B %Y")
    return f"""Today is {today}.

Here is today's data for Bremen:

Air Quality (OpenWeatherMap, measured {air_quality.get('measured_at')}):
- AQI index: {air_quality.get('aqi')} ({air_quality.get('aqi_label')})
- PM2.5: {air_quality.get('pm2_5')} µg/m³
- PM10: {air_quality.get('pm10')} µg/m³
- NO2: {air_quality.get('no2')} µg/m³
- O3: {air_quality.get('o3')} µg/m³
- SO2: {air_quality.get('so2')} µg/m³
- CO: {air_quality.get('co')} µg/m³

Traffic (TomTom, city center):
- Current average speed: {traffic.get('current_speed_kmh')} km/h
- Free-flow speed: {traffic.get('free_flow_speed_kmh')} km/h
- Congestion ratio: {traffic.get('congestion_ratio')}
- Road closure reported: {traffic.get('road_closure')}
- Confidence score: {traffic.get('confidence')}

Write a short "City Pulse" summary for Bremen (3 short paragraphs, or a couple \
of sentences each). Open with a warm, welcoming line about the city today. \
Then interpret what the air quality and traffic actually mean for someone \
walking, cycling, or driving around today — don't just restate the numbers. \
Close with a friendly, practical tip or note of local pride. Keep the overall \
length suitable for a daily newsletter or app notification — concise, not a \
full article."""


def generate_city_pulse(air_quality: dict[str, Any], traffic: dict[str, Any]) -> str:
    """Sends the collected data to Claude and returns the generated summary text."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": _build_user_prompt(air_quality, traffic)}
        ],
    )

    return "".join(block.text for block in message.content if block.type == "text")
