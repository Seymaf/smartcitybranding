# Bremen City Pulse — Smart City Brand Engine

A pipeline that pulls data across six of Bremen, Germany's smart city
components and turns it into three daily brand narratives — image,
positioning, and identity — using the Anthropic Claude API.

## The six components

| Component | Module | Data source |
| --- | --- | --- |
| Sustainability | [`air_quality.py`](air_quality.py) | [OpenWeatherMap Air Pollution API](https://openweathermap.org/api/air-pollution) (free tier, live) |
| Tourism | [`traffic.py`](traffic.py) | [TomTom Traffic Flow API](https://developer.tomtom.com/traffic-api/documentation/traffic-flow/flow-segment-data) (free tier, live) |
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

## How it works

1. **Fetch** — `main.py` calls all six fetchers: two live API calls
   (`fetch_air_quality`, `fetch_traffic`) and four reads from
   `manual_data.json` (`fetch_digital_infrastructure`, `fetch_e_governance`,
   `fetch_smart_communication`, `fetch_stakeholders`).
2. **Generate** — [`brand_engine.py`](brand_engine.py) sends all six
   datasets to Claude (`claude-opus-4-8`) in one structured-output call,
   which returns three grounded narratives:
   - **Brand image** — an emotional, sensory description of experiencing
     the city right now
   - **Brand positioning** — how the data suggests Bremen compares to peer
     cities in innovation and livability
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

| Variable               | Where to get it                                                                 | Notes                          |
| ----------------------- | -------------------------------------------------------------------------------- | ------------------------------- |
| `OPENWEATHER_API_KEY`   | [openweathermap.org/api](https://openweathermap.org/api)                        | Free tier covers the Air Pollution API |
| `TOMTOM_API_KEY`        | [developer.tomtom.com](https://developer.tomtom.com/)                           | Free tier covers Traffic Flow API |
| `ANTHROPIC_API_KEY`     | [console.anthropic.com](https://console.anthropic.com/)                         | Used to generate the narratives |

None of these keys are checked into the repo — `.env` is git-ignored, and
`.env.example` only holds placeholder values.

## Running

```bash
python main.py
```

This prints progress as it fetches each of the six data sources, then
prints the three generated brand narratives for Bremen.

## Updating manual data

`manual_data.json` holds one section per manually maintained component:

```json
{
  "digital_infrastructure": {
    "score": 7.2,
    "key_facts": ["...", "..."],
    "last_updated": "2026-06-01"
  },
  "e_governance": { "...": "..." },
  "smart_communication": { "...": "..." },
  "stakeholders": { "...": "..." }
}
```

- `score` — a 0–10 rating for the component.
- `key_facts` — a short list of concrete, citable facts Claude can draw on.
- `last_updated` — an ISO date (`YYYY-MM-DD`) so it's clear how fresh the
  data is.

Edit this file directly whenever you have updated figures; no code changes
are needed.

## Project structure

```
config.py                  # env var loading, shared constants, manual_data.json loader
air_quality.py              # OpenWeatherMap Air Pollution API client (sustainability)
traffic.py                  # TomTom Traffic Flow API client (tourism)
digital_infrastructure.py   # reads manual_data.json (no free live API available)
e_governance.py              # reads manual_data.json
smart_communication.py       # reads manual_data.json
stakeholders.py               # reads manual_data.json
manual_data.json             # manually maintained data for the four components above
brand_engine.py              # builds the prompt and calls Claude for the 3 brand narratives
city_pulse.py                 # earlier 2-component summary generator (kept, unused by main.py)
main.py                       # orchestrates the full pipeline end-to-end
```
