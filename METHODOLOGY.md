# Methodology

## Principles

1. **Measure before claiming.** Every score is built from metrics that were
   actually obtained on this run, from a published index entered with its
   citation, or from a clearly labelled curated assessment. Nothing is
   estimated to fill a gap.
2. **Show the evidence type.** Each metric is `measured` (live API),
   `benchmark` (published index) or `curated` (hand assessment), and is
   `city` level or a `national_proxy`. The report shows, per component, the
   share of evidence that is live-measured.
3. **Absence is information.** A component or value with no evidence is
   `n/a` and raises an integrity flag. It is never averaged in as a default.
4. **Self-assessment is checked against data.** When a curated assessment
   exceeds the live evidence in the same component by more than 25 points,
   the report says so (`CURATED_ABOVE_EVIDENCE`).

## Scoring

Every metric is normalized to 0–100.

- **Component score** = weighted mean of its metrics. Weight = connector
  weight (measured 1.0, benchmark 0.75, curated 0.5, provisional curated
  0.25) × 0.5 for national proxies.
- **Pillar score** = mean of the two components the source map assigns to
  it (Identity: Smart Communication + Digital Infrastructure; Image:
  E-Governance + Smart Tourism; Positioning: Stakeholders + Sustainability),
  over the components that have a score.
- **Vitality index** = mean of the pillar scores. Marked *not verifiable*
  unless ≥50% of all evidence weight is live-measured and every pillar has
  a score.
- **Values lens** = weighted mean of the metrics tagged with that value
  (democratic / participatory / innovative).

### Normalization ranges

`linear(a → b)` maps a to 0 and b to 100 (inverted when a > b);
`log(a → b)` does the same on a log10 scale, for volumes that span orders
of magnitude between small and large cities.

| Metric | Source | Normalization | Value tag |
| --- | --- | --- | --- |
| News volume (7 days) | GDELT | log(10 → 5,000 articles) | |
| News tone | GDELT | linear(-5 → +5) | |
| Community discussion (week) | Reddit | log(5 → 100 posts) | |
| Community reception | Reddit | linear(upvote ratio 0.5 → 1.0) | |
| Service requests (30 days) | Open311 | log(10 → 10,000) | participatory |
| Requests resolved | Open311 | share closed × 100 | participatory |
| Median days to resolve | Open311 | linear(30 → 1 days) | |
| Voice & accountability | World Bank WGI | linear(-2.5 → +2.5), national proxy | democratic, participatory |
| Rule of law / Control of corruption | World Bank WGI | linear(-2.5 → +2.5), national proxy | democratic |
| Government effectiveness | World Bank WGI | linear(-2.5 → +2.5), national proxy | |
| Open datasets | CKAN portal | log(10 → 10,000) | participatory |
| Datasets updated in last year | CKAN portal | share × 100 | participatory |
| Datasets on data.europa.eu | data.europa.eu | log(10 → 20,000) | participatory |
| Participatory processes / participants / proposals | Decidim | log(1 → 100) / log(100 → 100k) / log(10 → 20k) | participatory, democratic |
| Open job ads | Adzuna | log(500 → 100,000) | |
| Share of IT job ads | Adzuna | linear(2% → 15%) | innovative |
| FDI net inflows | World Bank | linear(-1% → 5% of GDP), national proxy | |
| Arrivals today / distinct origins | AviationStack | log(5 → 500) / linear(1 → 20) | |
| Arrivals yesterday / departure airports | OpenSky | log(5 → 1,000) / linear(1 → 60) | |
| Wikipedia views (30-day daily avg) | Wikimedia | log(100 → 50,000) | |
| Attraction rating / review volume | Google Places | linear(3.0 → 5.0) / log(1k → 1M) | |
| City-centre traffic fluidity | TomTom | (1 − congestion) × 100 | |
| Data-centre facilities / IXPs | PeeringDB | log(1 → 50) / linear(0 → 3) | innovative |
| Mobile cells in central 4 km² | OpenCelliD | log(10 → 2,000) | |
| AQI (1–5) / PM2.5 | OpenWeatherMap | linear(5 → 1) / linear(50 → 5 µg/m³) | |
| PM2.5 / NO2 (sensor average) | OpenAQ | linear(50 → 5) / linear(100 → 10 µg/m³) | |
| AQI (US scale) | AQICN | linear(200 → 0) | |
| Curated assessments | manual_data.json | rating × 10 | per section |
| Published indices | benchmarks.json | index's own range, or linear(rank total → 1) | per index |

5 µg/m³ PM2.5 and 10 µg/m³ NO2 are the WHO 2021 annual guidelines. These
ranges are deliberate, documented choices; change them in the connector
modules and update this table together.

## Source map coverage

**Implemented as live connectors (19):** GDELT, Reddit, Open311, World
Bank WGI, CKAN, data.europa.eu, Decidim, Adzuna, World Bank FDI (Data360),
AviationStack, OpenSky, Wikimedia Pageviews, Google Places, TomTom Traffic
API, PeeringDB, OpenCelliD, OpenAQ, AQICN, plus OpenWeatherMap (kept from
the original pipeline).

**Published indices → `benchmarks.json` (19 entries, filled by hand with
citations):** UN E-Participation Index, UN EGDI Online Service Component,
EU DESI, IESE Cities in Motion, ITU IDI, Transparency International CPI, WJP
Rule of Law Index, OECD DGI, World Bank GTMI, GFCI, StartupBlink, World Bank
B-READY, GDS-Index, TomTom Traffic Index, IMD Smart City Index, Network
Readiness Index, GSMA Mobile Connectivity Index, Yale EPI, ND-GAIN.

**Not implemented, and why:**

| Source | Reason |
| --- | --- |
| Brandwatch, Data365, Citibot, Granicus GXA, Vodafone Analytics, Telefónica Smart Steps, OpenGov PSP, fDi Markets, FlightAware, STR/Datarade, GSMA Intelligence, Euromonitor | Marked *PAID – reference only* in the source map |
| Botpress, WhatsApp Business Cloud API | Need a partnership with the city (its own logs / account) |
| Consul | Self-hosted; add alongside Decidim once a target city runs an instance |
| X (Twitter) free tier | Flagged in the source map as too thin for monitoring |
| APITube | Freemium news API; its response format couldn't be verified while building this, so it wasn't wired in blind |
| api.data.gov, SEC EDGAR | US-only; add for US cities |
| OpenCorporates | Requires an approved API account |
| Eurostat business demography | Needs the dataset code and JSON-stat parsing for the city's NUTS region; next candidate |
| Finnhub | National macro data; little city signal beyond the World Bank indicators |
| Hotel APIs | Availability/pricing aggregators; no stable free tier to verify against |
| Ookla open data, M-Lab | Bulk datasets (Parquet on S3, BigQuery), not request/response APIs; need an offline ingestion job |
| Google EIE, Climate TRACE, CDP Cities | Periodic datasets; to be added as benchmark-style entries or an ingestion job |
| UNWTO dashboard, WTTC cities report | Published reports without a comparable score; can be added to `benchmarks.json` |

## Maintaining curated data

`manual_data.json` holds 0–10 assessments for digital infrastructure,
e-governance, smart communication, stakeholders and local events (which
feeds Smart Tourism). They weigh half as much as a live measurement and
are always shown as assessments.

1. Update the section's score field only with a concrete, citable fact.
2. Keep `key_facts` specific; Claude receives them labelled as curated.
3. Set `last_updated` (`YYYY-MM-DD`).
4. Add a `note` when a value is an estimate; this halves its weight again.

Suggested cadence and where to look:

- **E-Governance:** quarterly. serviceStadt Bremen / bremen.de, the
  *e-Government – Made in Bremen* network, Innovationscampus für
  Verwaltungsdigitalisierung, Initiative D21 eGovernment Monitor.
- **Digital infrastructure:** semi-annually. Bundesnetzagentur
  Breitbandatlas, Bremen's regional broadband coordinator, operator
  coverage maps.
- **Stakeholders:** quarterly. WFB Bremen, Senate press releases,
  University of Bremen / Constructor University, bremenports.
- **Smart communication:** quarterly. The city's official channels,
  app-store reviews, the press office.
- **Local events:** monthly, and before festival season (Breminale,
  Musikfest Bremen, Open Space Domshof).

## Maintaining benchmarks

For each entry in `benchmarks.json`, take the value from the latest official
edition and fill `value`, `year` and `citation` (report title plus URL or
page). For rankings, also set `scale.total`. Entries with anything missing
are ignored by the pipeline.
