# Methodology: Hybrid Data Architecture

This project models Bremen's smart city profile across six components.
Sustainability is driven entirely by a live, free public API. Tourism
blends two live APIs (traffic, flight arrivals) with one manually curated
signal (local events) — no free API tracks "what's happening in Bremen
today." Smart communication is a similar hybrid: a manual audit of
Bremen's own citizen-facing channels, with a live global-news-mention
signal (GDELT) layered on top. The remaining three components have no
equivalent free, per-city, real-time API at all — so they're maintained
as periodically updated manual data instead. This document explains that
split, the reasoning behind it component by component, and how to keep
the manual data current.

## Why hybrid, not all-API or all-manual

An all-API approach isn't possible: no free service exposes a live,
per-city "e-governance maturity" or "citizen engagement quality" score —
these are qualitative, judgment-based assessments, not sensor readings. An
all-manual approach would throw away real, freely available live data for
air quality and traffic, which *do* have simple per-city REST APIs. The
hybrid model uses live data where it genuinely exists and is easy to get,
and transparent, dated manual data everywhere else — with a `last_updated`
field (and a `note` field for provisional data) so the brand narratives are
never presented as more current or more certain than they actually are.

## Real-time, API-driven components

| Component | Module(s) | API | What it fetches |
| --- | --- | --- | --- |
| Sustainability | [`air_quality.py`](air_quality.py) | [OpenWeatherMap Air Pollution API](https://openweathermap.org/api/air-pollution) (free tier) | AQI index + PM2.5, PM10, NO2, O3, SO2, CO concentrations |
| Tourism | [`traffic.py`](traffic.py) + [`flight_arrivals.py`](flight_arrivals.py) | [TomTom Traffic Flow API](https://developer.tomtom.com/traffic-api/documentation/traffic-flow/flow-segment-data) (free tier) + [AviationStack Flights API](https://aviationstack.com/) (free tier) | Current vs. free-flow speed, congestion ratio, road closures; plus today's arrival count, origin countries/cities, and notable patterns (e.g. "5 arrivals from Turkey") |

Both underlying APIs are simple, free, city-coordinate-keyed REST
endpoints — exactly the shape this pipeline needs — so they're queried
fresh on every `main.py` run. No manual step is needed or possible here;
the data is only ever as current as the last API response.

**Tourism is one component with three data sources, not three
components.** `traffic.py`, `flight_arrivals.py`, and `local_events.py`
are separate modules purely for code organization (different sources,
different response shapes). `main.py` combines their output into a single
`tourism` dict (`{"traffic": ..., "flight_arrivals": ..., "local_events":
...}`) before passing it to `brand_engine.py`, which formats it as one
"Tourism component" section — consistent with the six-component framework
(sustainability, tourism, digital infrastructure, e-governance, smart
communication, stakeholders).

**Flight arrivals is optional within tourism.** `fetch_flight_arrivals()`
never raises — if the API key is missing, the request fails, or the free
tier's rate limit is hit, it returns `{"available": False, "error": "..."}`
instead, and the tourism section is formatted without that subsection, no
mention of the outage. Two free-tier constraints shape the implementation:

- AviationStack's free plan is HTTP-only (HTTPS requires a paid plan), so
  the API key travels in the query string unencrypted. That's a limitation
  of AviationStack's tiering, not a choice made here.
- The real-time flights endpoint doesn't return a country per flight, only
  the departure airport's IATA code/name. A live per-flight country lookup
  would require a second API call per unique departure airport against
  AviationStack's separate Airports endpoint — impractical given the free
  tier's small monthly request quota. Instead, `flight_arrivals.py` maps a
  best-effort static table of common IATA codes (Bremen's typical
  European/leisure route network) to country names, falling back to the
  airport's own name for anything not in that table.

**Local events is the third tourism source, manually maintained.** See
"Local Events" below — it lives in `manual_data.json` alongside the four
standalone manual components, but conceptually feeds tourism rather than
being its own top-level component.

**Smart communication is a hybrid, like tourism.** No API measures
"citizen engagement quality" for a city's own communication channels, so
that half stays a manual audit in `manual_data.json` (see below). But how
much a city is talked about in global news right now *is* a free, live,
per-city-queryable signal — the [GDELT DOC 2.0 API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/)
needs no API key/signup and returns matching articles for a search term
within a chosen time window. `smart_communication.py` queries it for
"Bremen" over the last 24 hours on every run, derives a rough
`media_visibility_score` from the mention count, and adds a couple of
real headlines to `key_facts`. If the request fails, it falls back to the
manual data alone — this is an enrichment, not a required signal.

## Manually maintained data (periodic input)

Five sections read from [`manual_data.json`](manual_data.json) via a
shared loader (`config.load_manual_data`): four standalone components
(e-governance, digital infrastructure, stakeholders, smart communication)
plus local events, which feeds into the tourism component alongside
traffic and flight arrivals. Each was evaluated for a free real-time API
first; none exists for the manual data itself, for the reasons below.
(Smart communication is the exception that gets a live layer on top — see
"Smart communication is a hybrid" above — but its `manual_data.json`
section, the channels/chatbot audit, is still maintained the same way as
the other three.)

### E-Governance (`e_governance.py`)

- **Why manual:** No API measures "digital government maturity" for a
  single city. Assessing it means reading government portals, program
  announcements, and rollout press releases — inherently a judgment call,
  not a live metric a sensor or endpoint could report.
- **Recommended update frequency:** Quarterly, or immediately after a
  major service launch (a new online permit category, a new digital ID
  integration, etc.).
- **Data sources to consult:**
  - Bremen's official digital services portal (serviceStadt Bremen /
    bremen.de)
  - "e-Government – Made in Bremen" network announcements
  - Innovationscampus für Verwaltungsdigitalisierung updates
  - National eGovernment benchmarks (e.g. Initiative D21's eGovernment
    Monitor) for comparative context when scoring

### Digital Infrastructure (`digital_infrastructure.py`)

- **Why manual:** Live, per-city internet speed/connectivity data (e.g.
  Ookla) is either paid (Speedtest Intelligence API) or available only as a
  bulk historical dataset, not a queryable live endpoint. Rollout of fiber
  and 5G coverage also moves on a timescale of months, so live polling
  wouldn't add value even if it existed.
- **Recommended update frequency:** Semi-annually, or immediately after a
  significant rollout milestone (new fiber/5G coverage announcement).
- **Data sources to consult:**
  - Bundesnetzagentur Breitbandatlas (federal broadband atlas)
  - Bremen's Regional Broadband Center (regionaler Breitbandkoordinator)
    reports
  - Telecom provider coverage maps (Deutsche Telekom, Vodafone,
    Telefónica/O2) for 5G and fiber footprint
  - Bremen Senate digital infrastructure press releases

### Stakeholders (`stakeholders.py`)

- **Why manual:** Stakeholder ecosystem health — public-private
  partnerships, cross-department initiatives, academic collaborations — is
  a relational, qualitative assessment. No API tracks partnership strength.
- **Recommended update frequency:** Quarterly, or after a major
  partnership announcement (new MOU, initiative launch, funding award).
- **Data sources to consult:**
  - WFB Bremen (Wirtschaftsförderung Bremen) news and initiative pages
  - Bremen Senate press releases (Senatspressestelle)
  - University of Bremen / Jacobs University partnership announcements
  - bremenports Smart Port strategy updates
  - Governikus product and partnership announcements

### Smart Communication (`smart_communication.py`) — hybrid

- **Why the manual half is manual:** No API aggregates "citizen engagement
  quality" across a city's official communication channels. Assessing it
  requires an actual audit of social media activity, response rates, and
  app usage.
- **Current status:** ✅ **Verified.** `manual_data.json` now reflects a
  real audit of Bremen's official channels (tourism Instagram following and
  post cadence, WFB Bremen's dedicated tech channel, the discontinued city
  X/Twitter account) rather than the earlier placeholder estimate.
- **Recommended update frequency (manual half):** Quarterly — social
  platform strategy and follower/engagement figures shift slowly enough
  that a monthly check isn't necessary once a verified baseline is in place.
- **Data sources to consult (manual half):**
  - Official Bremen city social media accounts — posting frequency,
    engagement rates
  - Bremen city app / BSAG transit app store reviews and usage stats
  - City of Bremen press/communications office reports
  - Citizen e-participation platforms, if one exists for Bremen
- **The live half:** `_fetch_gdelt_mentions()` queries the GDELT DOC 2.0
  API for "Bremen" over the last 24 hours on every run — no update
  schedule needed, it's fetched fresh every time. See "Smart communication
  is a hybrid" above for why this doesn't need manual upkeep.

### Local Events (`local_events.py`) — feeds tourism, not standalone

- **Why manual:** No free API tracks "what festivals/events are running
  in Bremen right now" at the granularity this needs. Event calendars
  exist per-venue or per-organizer, not aggregated city-wide, and change
  on a seasonal rather than real-time basis.
- **Recommended update frequency:** Monthly, or immediately before major
  festival season (Breminale in July, Musikfest Bremen, and the
  mid-June-to-mid-September Open Space Domshof run) so the data reflects
  what's actually happening rather than a stale prior season.
- **Data sources to consult:**
  - Official Bremen tourism event calendar (bremen.de / visit.bremen)
  - Individual festival sites (Breminale, Musikfest Bremen, Open Space
    Domshof)
  - City of Bremen press/communications office event announcements

## How to update `manual_data.json`

1. Open `manual_data.json` and find the relevant top-level section
   (`e_governance`, `digital_infrastructure`, `stakeholders`,
   `smart_communication`, or `local_events`).
2. Update that section's score field. Each section uses its own field
   name (`digital_service_score`, `connectivity_score`,
   `partnership_score`, `engagement_score`, `activity_score`) on a
   **0–10 scale**. Only raise a score when you have a concrete fact to
   back it up — don't inflate scores speculatively.
3. Update `key_facts` — a short list of concrete, citable facts (not
   vague claims). These are what Claude quotes from directly in the brand
   narratives, so specificity matters more than length.
4. Set `last_updated` to today's date in `YYYY-MM-DD` format.
5. If a value is an estimate rather than a verified fact, add a `note`
   field explaining that (see `smart_communication` for the pattern).
   `brand_engine.py` is prompted to treat noted components with
   appropriately less certainty than verified ones.
6. Save the file. No code changes are required — every module reads
   `manual_data.json` fresh at runtime, so the next `python main.py` run
   picks up the update automatically.

## Daily archive → future weekly/monthly reports

Every `main.py` run writes `archive/<YYYY-MM-DD>.json` (see
[`archive.py`](archive.py)): the day's raw values from all eight fetchers
plus the three narratives with their cached/fresh status. Multiple runs on
the same day overwrite that day's file — the archive is a dated history
(one snapshot per day), not a per-run audit log.

This is the intended data source for future weekly/monthly report
generation: a report script can glob `archive/*.json`, read across a date
range, and track things like how `manual_data.json` scores moved over a
month, how often `brand_positioning` needed regenerating vs. served from
cache, or how sustainability/tourism signals trended week over week. Because
the archive is git-tracked (see README's "Daily archive" section for the
sensitivity reasoning), that history is available to whoever clones the
repo, not just whoever ran the pipeline locally.
