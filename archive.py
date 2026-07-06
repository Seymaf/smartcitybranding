"""Archives each day's raw component data and generated narratives.

Every main.py run overwrites that day's archive/<YYYY-MM-DD>.json with the
latest data — this builds a dated history (one file per day, not one per
run) that a future weekly/monthly report generator can read across many
days.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ARCHIVE_DIR = Path(__file__).parent / "archive"


def save_archive(
    raw_data: dict[str, Any], narratives: dict[str, dict[str, str]]
) -> Path:
    """Writes today's raw data + narratives to archive/<YYYY-MM-DD>.json.

    `raw_data` holds every component's fetched/read values for the day
    (air_quality, traffic, flight_arrivals, digital_infrastructure,
    e_governance, smart_communication, stakeholders, local_events).

    `narratives` maps each narrative name ("brand_image",
    "brand_positioning", "brand_identity") to
    {"text": ..., "status": "generated today" | "cached"}.

    Overwrites any existing file for today — this is a daily snapshot, not
    a per-run log.
    """
    ARCHIVE_DIR.mkdir(exist_ok=True)

    today = date.today().isoformat()
    archive_path = ARCHIVE_DIR / f"{today}.json"

    payload = {
        "date": today,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "raw_data": raw_data,
        "narratives": narratives,
    }

    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return archive_path
