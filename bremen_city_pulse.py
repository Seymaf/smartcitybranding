"""Bremen için günlük 'şehir nabzı' özeti üretir.

Hava kalitesi (AQICN) ve trafik (TomTom) verilerini çeker, ardından
Anthropic Claude API'sini kullanarak bu verilerden Türkçe bir günlük
özet metni oluşturur. Tüm API anahtarları .env dosyasından okunur.
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Any

import anthropic
import requests
from dotenv import load_dotenv
import os

load_dotenv()

# Bremen şehir merkezi koordinatları
BREMEN_LAT = 53.0793
BREMEN_LON = 8.8017

AQICN_API_TOKEN = os.environ.get("AQICN_API_TOKEN")
TOMTOM_API_KEY = os.environ.get("TOMTOM_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

REQUEST_TIMEOUT = 15


def fetch_air_quality() -> dict[str, Any]:
    """AQICN (waqi.info) üzerinden Bremen için hava kalitesi verisini çeker."""
    url = f"https://api.waqi.info/feed/geo:{BREMEN_LAT};{BREMEN_LON}/"
    response = requests.get(
        url, params={"token": AQICN_API_TOKEN}, timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    payload = response.json()

    if payload.get("status") != "ok":
        raise RuntimeError(f"AQICN API hatası: {payload.get('data')}")

    data = payload["data"]
    iaqi = data.get("iaqi", {})
    return {
        "aqi": data.get("aqi"),
        "dominant_pollutant": data.get("dominentpol"),
        "pm25": iaqi.get("pm25", {}).get("v"),
        "pm10": iaqi.get("pm10", {}).get("v"),
        "no2": iaqi.get("no2", {}).get("v"),
        "o3": iaqi.get("o3", {}).get("v"),
        "temperature": iaqi.get("t", {}).get("v"),
        "humidity": iaqi.get("h", {}).get("v"),
        "measured_at": data.get("time", {}).get("s"),
        "station": data.get("city", {}).get("name"),
    }


def fetch_traffic() -> dict[str, Any]:
    """TomTom Traffic Flow API üzerinden Bremen merkezi için trafik verisini çeker."""
    url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
    response = requests.get(
        url,
        params={
            "point": f"{BREMEN_LAT},{BREMEN_LON}",
            "key": TOMTOM_API_KEY,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    segment = response.json()["flowSegmentData"]

    current_speed = segment.get("currentSpeed")
    free_flow_speed = segment.get("freeFlowSpeed")
    congestion_ratio = (
        1 - (current_speed / free_flow_speed)
        if current_speed and free_flow_speed
        else None
    )

    return {
        "current_speed_kmh": current_speed,
        "free_flow_speed_kmh": free_flow_speed,
        "current_travel_time_s": segment.get("currentTravelTime"),
        "free_flow_travel_time_s": segment.get("freeFlowTravelTime"),
        "congestion_ratio": (
            round(congestion_ratio, 2) if congestion_ratio is not None else None
        ),
        "road_closure": segment.get("roadClosure", False),
        "confidence": segment.get("confidence"),
    }


def generate_city_pulse(air_quality: dict[str, Any], traffic: dict[str, Any]) -> str:
    """Toplanan veriden Claude ile günlük 'şehir nabzı' özetini üretir."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    today = datetime.now().strftime("%d.%m.%Y")
    user_prompt = f"""Bugünün tarihi: {today}

Bremen şehri için toplanan veriler:

Hava Kalitesi (AQICN, istasyon: {air_quality.get('station')}):
- Hava Kalitesi Endeksi (AQI): {air_quality.get('aqi')}
- Baskın kirletici: {air_quality.get('dominant_pollutant')}
- PM2.5: {air_quality.get('pm25')}
- PM10: {air_quality.get('pm10')}
- NO2: {air_quality.get('no2')}
- O3: {air_quality.get('o3')}
- Sıcaklık: {air_quality.get('temperature')} °C
- Nem: {air_quality.get('humidity')} %
- Ölçüm zamanı: {air_quality.get('measured_at')}

Trafik (TomTom, şehir merkezi):
- Mevcut ortalama hız: {traffic.get('current_speed_kmh')} km/s
- Serbest akış hızı: {traffic.get('free_flow_speed_kmh')} km/s
- Tıkanıklık oranı: {traffic.get('congestion_ratio')}
- Yol kapanışı: {traffic.get('road_closure')}
- Güven skoru: {traffic.get('confidence')}

Bu verilere dayanarak Bremen sakinleri için 3-4 paragraflık, günlük bir
"şehir nabzı" özet metni yaz. Hava kalitesinin ve trafiğin günlük yaşamı
nasıl etkileyebileceğini basit, anlaşılır bir dille açıkla. Sayısal
verileri yorumla, sadece tekrar etme. Türkçe yaz."""

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        system=(
            "Sen Bremen şehri için günlük durum özetleri hazırlayan bir "
            "şehir analistisin. Hava kalitesi ve trafik verilerini "
            "sentezleyerek vatandaşların anlayacağı, akıcı bir Türkçe "
            "özet metni üretiyorsun."
        ),
        messages=[{"role": "user", "content": user_prompt}],
    )

    return "".join(block.text for block in message.content if block.type == "text")


def main() -> int:
    missing = [
        name
        for name, value in [
            ("AQICN_API_TOKEN", AQICN_API_TOKEN),
            ("TOMTOM_API_KEY", TOMTOM_API_KEY),
            ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY),
        ]
        if not value
    ]
    if missing:
        print(
            f"Eksik ortam değişkenleri: {', '.join(missing)}. "
            ".env dosyanızı kontrol edin (bkz. .env.example).",
            file=sys.stderr,
        )
        return 1

    try:
        print("Hava kalitesi verisi çekiliyor...")
        air_quality = fetch_air_quality()

        print("Trafik verisi çekiliyor...")
        traffic = fetch_traffic()

        print("Şehir nabzı özeti üretiliyor...\n")
        summary = generate_city_pulse(air_quality, traffic)
    except requests.RequestException as exc:
        print(f"Veri çekilirken hata oluştu: {exc}", file=sys.stderr)
        return 1
    except (RuntimeError, KeyError) as exc:
        print(f"Veri işlenirken hata oluştu: {exc}", file=sys.stderr)
        return 1

    print("=" * 60)
    print(f"BREMEN ŞEHİR NABZI — {datetime.now().strftime('%d.%m.%Y')}")
    print("=" * 60)
    print(summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())
