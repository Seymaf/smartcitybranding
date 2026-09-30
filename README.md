# Smart City Branding — evidence-based city brand engine

**Mission:** identify cities (and global brands) that protect democratic,
participatory and innovative values, and show their brand value **without
greenwashing**.

The engine queries the sources in the *Smart City Components (API Source
Map)*, scores six smart city components, three branding pillars and the
three civic values, runs explicit integrity checks, and asks Claude to write
brand narratives that must cite the evidence they rest on. Bremen is the
default city.

## What makes it greenwashing-resistant

| Rule | Where it's enforced |
| --- | --- |
| No simulated or "baseline" values. A source either returns real data or is reported as `not configured` / `failed` / `empty`, and contributes nothing. | `connectors/base.py` |
| Every metric carries its source, URL, retrieval time, **evidence type** (measured / benchmark / curated) and **geographic level** (city / national proxy). | `core/models.py` |
| Components with no evidence get **no score** (`n/a`), not a default. Live measurements outweigh published indices (×0.75) and curated assessments (×0.5); national proxies count half. | `engine/scoring.py` |
| The headline vitality index is marked **not verifiable** unless ≥50% of the evidence weight is live-measured and every pillar has data. | `engine/scoring.py` |
| Integrity flags: `NO_EVIDENCE`, `SELF_REPORTED_ONLY`, `CURATED_ABOVE_EVIDENCE` (self-assessment >25 pts above live data), `SUSTAINABILITY_GAP` (poor measured air quality), `VALUE_UNEVIDENCED`. | `engine/scoring.py` |
| Claude only sees the evidence ledger and must return the ids it cites; unknown ids are surfaced as warnings. No API key → no narrative (no canned text). | `engine/brand_narrator.py` |
| Published indices (CPI, IMD, StartupBlink, …) stay empty in `benchmarks.json` until someone enters the value **with** its edition year and citation. | `connectors/curated/benchmarks.py` |

## Framework

| Smart city component | Branding pillar | Live sources implemented |
| --- | --- | --- |
| Smart Communication | City Identity | GDELT DOC API, Reddit Data API, Open311 |
| Digital Infrastructure | City Identity | TomTom Traffic, PeeringDB, OpenCelliD |
| E-Governance | City Image | World Bank WGI, CKAN open-data portal, data.europa.eu, Decidim |
| Smart Tourism | City Image | AviationStack, OpenSky, Wikimedia Pageviews, Google Places |
| Stakeholders | City Positioning | Adzuna, World Bank FDI |
| Sustainability | City Positioning | OpenWeatherMap, OpenAQ, AQICN |

Plus two cross-cutting sources: curated assessments (`manual_data.json`) and
published benchmarks (`benchmarks.json`). The **values lens** scores each
civic value from the metrics tagged with it — e.g. *democratic* from WGI
voice & accountability, rule of law, control of corruption (and CPI / WJP
once entered); *participatory* from open data, Open311, Decidim and the UN
E-Participation Index; *innovative* from tech-job share, data-centre / IXP
presence, and innovation rankings.

See [`METHODOLOGY.md`](METHODOLOGY.md) for every normalization range and for
the source-map rows that are intentionally not implemented, and why.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in whichever keys you have
```

**Every key is optional.** Sources without a key are listed as "not
configured". These need no key at all: GDELT, Wikimedia, World Bank
(WGI + FDI), PeeringDB, data.europa.eu, and the CKAN portal.

| Variable | Source | Sign up |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Brand narratives | [console.anthropic.com](https://console.anthropic.com/) |
| `OPENWEATHER_API_KEY` | Air quality (modelled) | [openweathermap.org/api](https://openweathermap.org/api) |
| `OPENAQ_API_KEY` | Air quality (sensors) | [explore.openaq.org/register](https://explore.openaq.org/register) |
| `AQICN_TOKEN` | Air quality (stations) | [aqicn.org/data-platform/token](https://aqicn.org/data-platform/token/) |
| `TOMTOM_API_KEY` | Traffic flow | [developer.tomtom.com](https://developer.tomtom.com/) |
| `AVIATIONSTACK_API_KEY` | Today's arrivals | [aviationstack.com](https://aviationstack.com/) |
| `OPENSKY_CLIENT_ID` / `_SECRET` | Yesterday's arrivals | [opensky-network.org](https://opensky-network.org/) → Account → API client |
| `REDDIT_CLIENT_ID` / `_SECRET` | Community discussion | [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) (script app) |
| `ADZUNA_APP_ID` / `_KEY` | Job market | [developer.adzuna.com](https://developer.adzuna.com/) |
| `GOOGLE_PLACES_API_KEY` | Attraction ratings | [Google Cloud console](https://console.cloud.google.com/) (Places API (New)) |
| `OPENCELLID_API_KEY` | Cell-tower density | [opencellid.org](https://opencellid.org/) |

City-specific endpoints (an Open311 server, a Decidim instance, the city's
own CKAN portal) are set on `CityContext` in `core/models.py`. Bremen
currently has no public Open311 or Decidim endpoint, so those two report
"not configured".

## Running

```bash
python main.py                 # full run: sources, scores, checks, narratives, archive
python main.py --no-narratives # skip Claude
python main.py --refresh       # regenerate positioning/identity even if cached
python -m pytest               # tests (pip install -r requirements-dev.txt)
```

The report lists every source's status, the evidence coverage, the scores
(with the share of each component that is live-measured), the integrity
flags, and the narratives with the evidence ids they cite.

**Narratives:** `brand_image` is regenerated every run. `brand_positioning`
and `brand_identity` are cached in `cached_narratives.json` (git-ignored)
until the slow-moving evidence changes (curated data, benchmarks, annual
national indicators).

**Archive:** each run writes `archive/<YYYY-MM-DD>.json` (the full scored
pulse plus every raw observation; one file per day, overwritten by later
runs that day). It's git-tracked so the history can feed weekly/monthly
reports. It holds only public data and generated text; credentials are
redacted from error messages before they're stored.

## Maintaining curated data and benchmarks

- `manual_data.json` — 0–10 assessments with `key_facts`, `last_updated`
  and an optional `note` for provisional values (which halves their weight).
  Only raise a score with a concrete, citable fact behind it.
- `benchmarks.json` — one entry per published index from the source map.
  Fill `value`, `year` and `citation` from the official edition (and
  `scale.total` for rankings). Anything left `null` is ignored.

## Project structure

```
core/            models (evidence-aware metrics), config & credential redaction
connectors/      one module per source, grouped by component; registry.py lists them all
  base.py        connector contract, HTTP helpers, normalization helpers
engine/
  scoring.py     component / pillar / values scores + integrity flags
  brand_narrator.py  Claude narratives grounded in the evidence ledger
  narrative_cache.py positioning/identity cache
  orchestrator.py    runs everything, writes the archive
main.py          CLI
manual_data.json curated assessments
benchmarks.json  published indices (fill with citations)
tests/           connector tests against canned API responses + engine tests
web/             marketing site pages
```
