# Methodology: Hybrid Data Architecture

This project models Bremen's smart city profile across six components. Two
are driven by live, free public APIs. The other four have no equivalent
free, per-city, real-time API — so they're maintained as periodically
updated manual data instead. This document explains that split, the
reasoning behind it component by component, and how to keep the manual data
current.

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

| Component | Module | API | What it fetches |
| --- | --- | --- | --- |
| Sustainability | [`air_quality.py`](air_quality.py) | [OpenWeatherMap Air Pollution API](https://openweathermap.org/api/air-pollution) (free tier) | AQI index + PM2.5, PM10, NO2, O3, SO2, CO concentrations |
| Tourism | [`traffic.py`](traffic.py) | [TomTom Traffic Flow API](https://developer.tomtom.com/traffic-api/documentation/traffic-flow/flow-segment-data) (free tier) | Current vs. free-flow speed, congestion ratio, road closures |

Both are simple, free, city-coordinate-keyed REST endpoints — exactly the
shape this pipeline needs — so they're queried fresh on every `main.py` run.
No manual step is needed or possible here; the data is only ever as current
as the last API response.

## Manually maintained components (periodic input)

All four read from [`manual_data.json`](manual_data.json) via a shared
loader (`config.load_manual_data`). Each was evaluated for a free real-time
API first; none exists, for the reasons below.

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

### Smart Communication (`smart_communication.py`)

- **Why manual:** No API aggregates "citizen engagement quality" across a
  city's official communication channels. Assessing it requires an actual
  audit of social media activity, response rates, and app usage.
- **Current status:** ⚠️ **Placeholder.** The current `engagement_score`
  and `key_facts` in `manual_data.json` are provisional estimates, marked
  explicitly via the `note` field. This is the highest-priority component
  to replace with real research.
- **Recommended update frequency:** Monthly until a verified baseline
  replaces the placeholder, then quarterly thereafter.
- **Data sources to consult:**
  - Official Bremen city social media accounts — posting frequency,
    engagement rates
  - Bremen city app / BSAG transit app store reviews and usage stats
  - City of Bremen press/communications office reports
  - Citizen e-participation platforms, if one exists for Bremen

## How to update `manual_data.json`

1. Open `manual_data.json` and find the relevant top-level section
   (`e_governance`, `digital_infrastructure`, `stakeholders`, or
   `smart_communication`).
2. Update that section's score field. Each component uses its own field
   name (`digital_service_score`, `connectivity_score`,
   `partnership_score`, `engagement_score`) on a **0–10 scale**. Only
   raise a score when you have a concrete fact to back it up — don't
   inflate scores speculatively.
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
