# Next steps: remaining candidate data sources

[`data_sources_api_map.csv`](data_sources_api_map.csv) is a research map of
candidate APIs for expanding this pipeline's smart city components, scored
across free/paid, live/dataset, and city-level granularity. Three rows from
it are already integrated (see below); this file tracks what's left.

## Already integrated

| CSV row | Component | Module |
| --- | --- | --- |
| GDELT 2.0 / DOC API (Public Perception) | Smart Communication | [`smart_communication.py`](smart_communication.py) |
| PeeringDB API (Digital Infrastructure Presence) | Digital Infrastructure | [`digital_infrastructure.py`](digital_infrastructure.py) |
| Wikimedia Pageviews API (Visitor Digital Interest) | Smart Tourism | [`wikipedia_interest.py`](wikipedia_interest.py) |

Each follows the same pattern: keep the existing manual/live core, layer
the new API on top as an additional metric + a few `key_facts`, and degrade
gracefully (never raise) if the new source is unreachable. Follow this
pattern for anything below.

## Remaining, by CSV component

**Smart Communication** — `smart_communication.py` / new modules
- Public Perception (alt/complement to GDELT): APITube, Reddit Data API
- Citizen ↔ Machine Interaction: **Open311 API** (free, standard) — highest
  priority here, *if* Bremen (or a peer city) publishes an Open311
  endpoint; verify before building
- Network-Level Signal: OpenCelliD (crowdsourced cell-tower density)
- Benchmark & Validation: UN E-Participation Index, EU DESI, IESE Cities in
  Motion Index, ITU IDI — all published-report datasets (no live API), so
  these would need a periodic manual read rather than a fetcher

**E-Governance** — `e_governance.py` is currently fully manual
- Open Data & Transparency: api.data.gov, CKAN, data.europa.eu — dataset
  catalogs, not a maturity score; unclear direct fit
- Digital Participation & Civic Tech: **Decidim**/**Consul** — only useful
  if Bremen runs a self-hosted instance
- Institutional Quality (national-level proxy, not Bremen-specific): World
  Bank WGI, Transparency International CPI, WJP Rule of Law Index
- Benchmark: UN EGDI, OECD DGI, World Bank GTMI

**Stakeholders** — `stakeholders.py` is currently fully manual
- Corporate Presence: **OpenCorporates API** (freemium, daily limit) —
  registration volume by city
- Investment & Capital Flows: SEC EDGAR full-text search (free, US-listed
  only), Finnhub (freemium, national-level)
- Labor Market: **Adzuna API** (free tier) — job-posting volume/salary by
  city, decent Bremen fit
- Benchmark: GFCI, StartupBlink, World Bank B-READY

**Smart Tourism** — `traffic.py` + `flight_arrivals.py` + `wikipedia_interest.py` + `local_events.py`
- Air & Ground Arrivals: **OpenSky Network** was the CSV's free
  alternative/complement to AviationStack, but OpenSky moved most of its
  REST API behind free OAuth2 registration around 2023 — confirm current
  terms before treating it as a no-signup source
- Accommodation & Demand: Hotel APIs (freemium aggregators) — occupancy/demand proxy
- Benchmark: UNWTO dashboard, GDS-Index, WTTC Cities Economic Impact

**Digital Infrastructure** — `digital_infrastructure.py`
- Network Performance: Ookla Speedtest Open Data (bulk dataset, not a live
  endpoint — same limitation the README already documents), M-Lab NDT (open
  but requires BigQuery access, more setup than the others)
- Benchmark: IMD Smart City Index, Network Readiness Index, GSMA Mobile
  Connectivity Index

**Sustainability** — `air_quality.py` (already live via OpenWeatherMap)
- Air Quality alternates/complements: AQICN, IQAir AirVisual
- Emissions & Climate: Google Environmental Insights Explorer, Climate TRACE
- Civic Climate Disclosure: **CDP Cities Disclosure API** — Bremen's
  self-reported climate targets, decent fit if Bremen discloses to CDP
- Benchmark: Yale/Columbia EPI, ND-GAIN

## Notes for whoever picks this up

- Rows marked `[PAID - reference only]` in the CSV are out of scope — this
  project only uses free/no-key or generous-free-tier APIs.
- "Benchmark & Validation" rows are almost all published reports/datasets,
  not live REST endpoints — they're better suited to an occasional manual
  `key_facts` update (like `manual_data.json` already does) than a fetcher
  module.
- Test any new source's actual response shape before wiring it in — API
  docs and CSV descriptions can be stale or optimistic (see the OpenSky
  note above).
