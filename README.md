# Bremen City Pulse — Smart City Brand Engine

A pipeline that pulls data across six of Bremen, Germany's smart city
components and turns it into three daily brand narratives — image,
positioning, and identity — using the Anthropic Claude API.

## The six components

| Component | Module(s) | Data source |
| --- | --- | --- |
| Sustainability | [`air_quality.py`](air_quality.py) | [OpenWeatherMap Air Pollution API](https://openweathermap.org/api/air-pollution) (free tier, live) |
| Tourism | [`traffic.py`](traffic.py) + [`flight_arrivals.py`](flight_arrivals.py) + [`wikipedia_interest.py`](wikipedia_interest.py) + [`local_events.py`](local_events.py) | [TomTom Traffic Flow API](https://developer.tomtom.com/traffic-api/documentation/traffic-flow/flow-segment-data) (free tier, live) + [AviationStack Flights API](https://aviationstack.com/) (free tier, live) + [Wikimedia Pageviews API](https://wikimedia.org/api/rest_v1/) (free, no key required, live) + `manual_data.json` — see note below |
| Digital infrastructure | [`digital_infrastructure.py`](digital_infrastructure.py) | `manual_data.json` (fiber/5G rollout audit) + [PeeringDB API](https://www.peeringdb.com/apidocs/) (free, no key required, live interconnection-facility presence) |
| E-governance | [`e_governance.py`](e_governance.py) | `manual_data.json` |
| Smart communication | [`smart_communication.py`](smart_communication.py) | `manual_data.json` (citizen-facing channels/chatbot ecosystem) + [GDELT DOC 2.0 API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) (free, no key required, live global news mentions) |
| Stakeholders | [`stakeholders.py`](stakeholders.py) | `manual_data.json` |

**Smart communication is a hybrid, like tourism:** the manual audit of
Bremen's own chatbot/social-media ecosystem stays in `manual_data.json` —
no API measures "citizen engagement quality" for a city's own channels —
but `smart_communication.py` layers a live `media_visibility_score` and a
couple of real headlines on top, fetched fresh from GDELT on every run.
GDELT needs no API key, and the module falls back to manual-only data if
the request fails, so this never blocks the pipeline.

**Digital infrastructure is a hybrid too, for a different reason:** there's
no simple free, queryable REST API for city-level internet *speed* —
Ookla's live data sits behind the paid Speedtest Intelligence API, and its
free option (Ookla Open Data on AWS) is a bulk historical Parquet dataset,
not a "give me today's number for Bremen" endpoint. So the manual
`connectivity_score`/`key_facts` audit stays. But `digital_infrastructure.py`
now also layers on a live `infrastructure_presence_score` from the
PeeringDB API (free, no key) — how many internet exchange/data-centre
facilities are registered in Bremen right now. It's a presence signal, not
a speed measurement, and falls back to manual-only data if PeeringDB is
unreachable.

**Tourism has four data sources, not four components:** `traffic.py`,
`flight_arrivals.py`, `wikipedia_interest.py`, and `local_events.py` are
separate modules for code organization, but `main.py` combines their
output into one `tourism` dict before handing it to `brand_engine.py`, and
the prompt presents it as a single "Tourism component" with a traffic
subsection, a flight arrivals subsection, a Wikipedia interest subsection,
and a local events subsection — not four independent inputs.

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
- `wikipedia_interest.py` fetches Bremen's English Wikipedia pageviews over
  a 7-day window (via the free, no-key Wikimedia Pageviews API) as a proxy
  for global research/travel interest. Also optional, following the same
  pattern as flight arrivals: any failure returns an "unavailable" summary
  rather than raising.
- `local_events.py` reads Bremen's current festivals/events (e.g.
  Breminale, Musikfest Bremen, Open Space Domshof) from `manual_data.json`
  — no free API tracks "what's happening in Bremen right now" either, so
  this follows the same manual pattern as digital infrastructure,
  e-governance, smart communication, and stakeholders.

## How it works

1. **Fetch** — `main.py` calls `fetch_air_quality`, plus `fetch_traffic` +
   `fetch_flight_arrivals` + `fetch_wikipedia_interest` + `fetch_local_events`
   (combined into one `tourism` dict), and four component fetchers that each
   start from `manual_data.json` (`fetch_digital_infrastructure`,
   `fetch_e_governance`, `fetch_smart_communication`, `fetch_stakeholders`)
   — two of which (digital infrastructure, smart communication) also layer
   on a live, no-key API call (PeeringDB, GDELT respectively).
2. **Generate** — [`brand_engine.py`](brand_engine.py) makes two Claude
   (`claude-opus-4-8`) calls:
   - **Brand image** — an emotional, sensory description of experiencing
     the city right now (a currently running festival is especially
     useful evidence here). Generated on **every run** — it's grounded in
     live data that changes constantly, so caching it wouldn't reflect
     today's reality.
   - **Brand positioning** (how the data suggests Bremen compares to peer
     cities in innovation and livability — flight arrival origins, when
     available, are especially useful evidence here) and **brand
     identity** (a short statement of the city's distinct character) are
     generated together and **cached** — see below.
3. **Print** — `main.py` prints all three narratives under clear labels,
   marking each as `(generated today)` or `(cached)`.

## Caching brand positioning and identity

`brand_positioning` and `brand_identity` lean mostly on the slower-moving
manual components (digital infrastructure, e-governance, smart
communication, stakeholders, local events), so there's no reason to pay
for a fresh Claude call for them on every run. [`narrative_cache.py`](narrative_cache.py)
writes them to `cached_narratives.json` (git-ignored — it's a local
runtime cache, not something to commit) alongside a fingerprint of every
`manual_data.json` section's `last_updated` value.

On each run:

- If `cached_narratives.json` exists and every section's `last_updated`
  still matches the fingerprint, the cached positioning/identity are
  reused — no Claude call.
- If any `last_updated` value has changed (or there's no cache yet), both
  are regenerated and the cache is rewritten with the new fingerprint.
- Passing `--refresh` forces regeneration regardless of the fingerprint:

  ```bash
  python main.py --refresh
  ```

`brand_image` is unaffected by any of this — it always calls Claude fresh.

## Daily archive

Every `main.py` run writes that day's complete snapshot to
[`archive.py`](archive.py) → `archive/<YYYY-MM-DD>.json` — the raw data
from all nine fetchers (air quality, traffic, flight arrivals, Wikipedia
interest, local events, digital infrastructure, e-governance, smart
communication, stakeholders) plus the three narratives, each tagged `"generated today"`
or `"cached"`. Running `main.py` more than once on the same day
**overwrites** that day's file — it's a daily snapshot, not a per-run log.
This is meant to accumulate into a dated history that a future
weekly/monthly report generator can read across many days.

**`archive/` is git-tracked, not git-ignored.** Unlike `.env` and
`cached_narratives.json`, nothing in an archive file is a secret: it's
publicly-sourced air quality/traffic/flight-count data, the manually
curated component facts, and generated marketing copy — no API keys, no
personal data. (`flight_arrivals.py`'s error messages are explicitly
redacted of API key values via `config.redact_secrets` before they can
reach an archive file or the console — see the note in that module.)
Since the whole point of this archive is to build a history usable by a
future report generator, it needs to persist and be shareable across
environments, which argues for committing it rather than leaving it
local-only.

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

# Force brand_positioning and brand_identity to regenerate even if
# manual_data.json hasn't changed since the last cache:
python main.py --refresh
```

This prints progress as it fetches each component's data (tourism logs as
one step covering traffic, flight arrivals, and local events), then prints
the three generated brand narratives for Bremen, each labeled
`(generated today)` or `(cached)`.

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
wikipedia_interest.py         # Wikimedia Pageviews API client (tourism, optional, no key needed)
local_events.py               # reads manual_data.json (tourism: festivals/events)
digital_infrastructure.py   # manual_data.json + live PeeringDB facility presence (no key needed)
e_governance.py              # reads manual_data.json
smart_communication.py       # manual_data.json + live GDELT DOC 2.0 mentions (no key needed)
stakeholders.py               # reads manual_data.json
manual_data.json             # manually maintained data for the five sections above
brand_engine.py              # builds prompts and calls Claude for the 3 brand narratives
narrative_cache.py            # caches brand_positioning/brand_identity in cached_narratives.json
cached_narratives.json         # runtime cache (git-ignored, created on first run)
archive.py                    # writes each day's snapshot to archive/<date>.json
archive/                       # one JSON file per day (git-tracked — see "Daily archive" above)
city_pulse.py                 # earlier 2-component summary generator (kept, unused by main.py)
main.py                       # orchestrates the full pipeline end-to-end
```
