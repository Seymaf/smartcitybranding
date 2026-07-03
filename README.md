# Bremen City Pulse — Smart City Brand Engine

A pipeline that pulls data across six of Bremen, Germany's smart city
components and turns it into three daily brand narratives — image,
positioning, and identity — using the Anthropic Claude API.

## The six components

| Component | Module(s) | Data source |
| --- | --- | --- |
| Sustainability | [`air_quality.py`](air_quality.py) | [OpenWeatherMap Air Pollution API](https://openweathermap.org/api/air-pollution) (free tier, live) |
| Tourism | [`traffic.py`](traffic.py) + [`flight_arrivals.py`](flight_arrivals.py) + [`local_events.py`](local_events.py) | [TomTom Traffic Flow API](https://developer.tomtom.com/traffic-api/documentation/traffic-flow/flow-segment-data) (free tier, live) + [AviationStack Flights API](https://aviationstack.com/) (free tier, live) + `manual_data.json` — see note below |
| Digital infrastructure | [`digital_infrastructure.py`](digital_infrastructure.py) | `manual_data.json` (see note below) |
| E-governance | [`e_governance.py`](e_governance.py) | `manual_data.json` |
| Smart communication | [`smart_communication.py`](smart_communication.py) | `manual_data.json` |
| Stakeholders | [`stakeholders.py`](stakeholders.py) | `manual_data.json` |

**Why digital infrastructure is manual too:** there's no simple free,
queryable REST API for city-level internet speed/connectivity comparable to
OpenWeatherMap or TomTom. Ookla's live data sits behind the paid Speedtest
Intelligence API; its free option (Ookla Open Data on AWS) is a bulk
historical Parquet dataset meant for offline analysis, not a
"give me today's number for Bremen" endpoint. So `digital_infrastructure.py`
follows the same `manual_data.json` pattern as the other three components.

**Tourism has three data sources, not three components:** `traffic.py`,
`flight_arrivals.py`, and `local_events.py` are separate modules for code
organization, but `main.py` combines their output into one `tourism` dict
before handing it to `brand_engine.py`, and the prompt presents it as a
single "Tourism component" with a traffic subsection, a flight arrivals
subsection, and a local events subsection — not three independent inputs.

- `flight_arrivals.py` fetches today's arrivals at Bremen Airport (BRE)
  and summarizes total arrival count, origin countries/cities, and
  notable patterns (e.g. "5 arrivals from Turkey"). It's optional: if
  `AVIATIONSTACK_API_KEY` is unset, or the API is rate-limited or errors,
  the module returns an "unavailable" summary instead of raising, and the
  tourism section is formatted without that subsection — no mention of
  the outage. AviationStack's free tier is HTTP-only (no HTTPS) and
  doesn't return a country field per flight, so this module maps a
  best-effort static table of common departure airport codes to
  countries, falling back to the airport name otherwise.
- `local_events.py` reads Bremen's current festivals/events (e.g.
  Breminale, Musikfest Bremen, Open Space Domshof) from `manual_data.json`
  — no free API tracks "what's happening in Bremen right now" either, so
  this follows the same manual pattern as digital infrastructure,
  e-governance, smart communication, and stakeholders.

## How it works

1. **Fetch** — `main.py` calls `fetch_air_quality`, plus `fetch_traffic` +
   `fetch_flight_arrivals` + `fetch_local_events` (combined into one
   `tourism` dict), and four reads from `manual_data.json`
   (`fetch_digital_infrastructure`, `fetch_e_governance`,
   `fetch_smart_communication`, `fetch_stakeholders`).
2. **Generate** — [`brand_engine.py`](brand_engine.py) sends all six
   components to Claude (`claude-opus-4-8`) in one structured-output call,
   which returns three grounded narratives:
   - **Brand image** — an emotional, sensory description of experiencing
     the city right now (a currently running festival is especially
     useful evidence here)
   - **Brand positioning** — how the data suggests Bremen compares to peer
     cities in innovation and livability (flight arrival origins, when
     available, are especially useful evidence here)
   - **Brand identity** — a short statement of the city's distinct
     character today
3. **Print** — `main.py` prints all three narratives under clear labels.

`city_pulse.py` is an earlier, simpler two-component (air quality + traffic)
summary generator. It's kept in the repo for reference but is no longer
wired into `main.py`.

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Create your `.env` file from the template:

   ```bash
   cp .env.example .env
   ```

3. Fill in `.env` with your API keys (see below).

4. Review `manual_data.json` and edit the `score`, `key_facts`, and
   `last_updated` values for `digital_infrastructure`, `e_governance`,
   `smart_communication`, and `stakeholders` — the starter values in the
   repo are placeholders for you to replace with real figures.

## Required API keys

| Variable                 | Where to get it                                          | Notes                                   |
| ------------------------- | ---------------------------------------------------------- | ----------------------------------------- |
| `OPENWEATHER_API_KEY`     | [openweathermap.org/api](https://openweathermap.org/api) | Free tier covers the Air Pollution API   |
| `TOMTOM_API_KEY`          | [developer.tomtom.com](https://developer.tomtom.com/)    | Free tier covers Traffic Flow API        |
| `ANTHROPIC_API_KEY`       | [console.anthropic.com](https://console.anthropic.com/)  | Used to generate the narratives          |
| `AVIATIONSTACK_API_KEY`   | [aviationstack.com](https://aviationstack.com/)           | Optional — free tier; flight_arrivals.py degrades gracefully if unset |

None of these keys are checked into the repo — `.env` is git-ignored, and
`.env.example` only holds placeholder values.

## Running

```bash
python main.py
```

This prints progress as it fetches each component's data (tourism logs as
one step covering traffic, flight arrivals, and local events), then prints
the three generated brand narratives for Bremen.

## Updating manual data

`manual_data.json` holds one section per manually maintained data source
(four of these feed their own top-level component; `local_events` feeds
into the tourism component alongside traffic and flight arrivals). Each
section uses its own score field name:

```json
{
  "digital_infrastructure": {
    "connectivity_score": 9,
    "key_facts": ["...", "..."],
    "last_updated": "2026-07-03"
  },
  "e_governance": { "digital_service_score": 7, "key_facts": ["..."], "last_updated": "2026-07-03" },
  "smart_communication": { "engagement_score": 7, "key_facts": ["..."], "last_updated": "2026-07-03" },
  "stakeholders": { "partnership_score": 8, "key_facts": ["..."], "last_updated": "2026-07-03" },
  "local_events": { "activity_score": 8, "key_facts": ["..."], "last_updated": "2026-07-03" }
}
```

- Score field — a 0–10 rating for the section (`connectivity_score`,
  `digital_service_score`, `engagement_score`, `partnership_score`,
  `activity_score`).
- `key_facts` — a short list of concrete, citable facts Claude can draw on.
- `last_updated` — an ISO date (`YYYY-MM-DD`) so it's clear how fresh the
  data is.
- `note` (optional) — flags a value as an estimate/placeholder rather than
  verified data; `brand_engine.py` treats noted components with
  appropriately less certainty. Omit this key once the data is verified.

Edit this file directly whenever you have updated figures; no code changes
are needed. See [`METHODOLOGY.md`](METHODOLOGY.md) for per-component update
frequency and which sources to consult.

## Project structure

```
config.py                  # env var loading, shared constants, manual_data.json loader
air_quality.py              # OpenWeatherMap Air Pollution API client (sustainability)
traffic.py                  # TomTom Traffic Flow API client (tourism)
flight_arrivals.py           # AviationStack Flights API client (tourism, optional)
local_events.py               # reads manual_data.json (tourism: festivals/events)
digital_infrastructure.py   # reads manual_data.json (no free live API available)
e_governance.py              # reads manual_data.json
smart_communication.py       # reads manual_data.json
stakeholders.py               # reads manual_data.json
manual_data.json             # manually maintained data for the five sections above
brand_engine.py              # builds the prompt and calls Claude for the 3 brand narratives
city_pulse.py                 # earlier 2-component summary generator (kept, unused by main.py)
main.py                       # orchestrates the full pipeline end-to-end
```
