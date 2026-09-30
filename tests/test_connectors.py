"""Each connector against canned responses shaped like the real API."""
from __future__ import annotations

from datetime import date

import pytest
import requests

from connectors.communication.gdelt import GDELTNewsConnector
from connectors.communication.open311 import Open311Connector
from connectors.communication.reddit import RedditConnector
from connectors.curated.benchmarks import BenchmarksConnector, benchmark_score, is_filled
from connectors.curated.manual_data import CuratedDataConnector
from connectors.digital.opencellid import OpenCelliDConnector
from connectors.digital.peeringdb import PeeringDBConnector
from connectors.digital.tomtom import TomTomTrafficConnector
from connectors.governance.ckan import CKANOpenDataConnector
from connectors.governance.data_europa import DataEuropaConnector
from connectors.governance.decidim import DecidimConnector
from connectors.governance.world_bank_wgi import WorldBankGovernanceConnector
from connectors.stakeholders.adzuna import AdzunaConnector
from connectors.stakeholders.world_bank_fdi import WorldBankFDIConnector
from connectors.sustainability.aqicn import AQICNConnector
from connectors.sustainability.openaq import OpenAQConnector
from connectors.sustainability.openweather import OpenWeatherAirConnector
from connectors.tourism.aviationstack import AviationStackConnector
from connectors.tourism.google_places import GooglePlacesConnector
from connectors.tourism.opensky import OpenSkyConnector
from connectors.tourism.wikimedia import WikimediaPageviewsConnector
from core.models import CityContext, EvidenceType, GeoLevel, SmartCityComponent, SourceStatus, ValueDimension

CITY = CityContext()


def names(metrics):
    return {m.name: m for m in metrics}


# ---- behaviour shared by all connectors -----------------------------------


@pytest.mark.parametrize("connector", [
    RedditConnector(), AdzunaConnector(), AviationStackConnector(), OpenSkyConnector(), GooglePlacesConnector(),
    TomTomTrafficConnector(), OpenCelliDConnector(), OpenWeatherAirConnector(), OpenAQConnector(), AQICNConnector(),
])
def test_missing_key_is_not_configured_and_makes_no_request(connector, http):
    obs, metrics = connector.run(CITY)
    assert obs.status == SourceStatus.NOT_CONFIGURED
    assert metrics == []
    assert http.calls == []


@pytest.mark.parametrize("connector", [Open311Connector(), DecidimConnector()])
def test_city_endpoint_connectors_skip_without_endpoint(connector, http):
    obs, metrics = connector.run(CITY)
    assert obs.status == SourceStatus.NOT_CONFIGURED and metrics == [] and http.calls == []


def test_failure_is_reported_without_leaking_the_key(http, creds):
    creds("TOMTOM_API_KEY")
    http.add("api.tomtom.com", requests.HTTPError("403 for url ...?key=test-tomtom_api_key-secret"))
    obs, metrics = TomTomTrafficConnector().run(CITY)
    assert obs.status == SourceStatus.ERROR and metrics == []
    assert "secret" not in obs.error and "[REDACTED]" in obs.error


# ---- Smart Communication ---------------------------------------------------


def test_gdelt(http):
    http.add("gdeltproject", {"timeline": [{"series": "Article Count", "data": [{"date": "x", "value": 40}, {"date": "y", "value": 60}]}]},
             when=lambda p: p["mode"] == "timelinevolraw")
    http.add("gdeltproject", {"timeline": [{"series": "Average Tone", "data": [{"date": "x", "value": 1.0}, {"date": "y", "value": 2.0}]}]},
             when=lambda p: p["mode"] == "timelinetone")
    obs, metrics = GDELTNewsConnector().run(CITY)
    assert obs.data["articles"] == 100 and obs.data["average_tone"] == 1.5
    m = names(metrics)
    assert m["news_tone"].score == 65.0
    assert 0 < m["news_volume"].score < 100
    assert all(x.evidence_type == EvidenceType.MEASURED for x in metrics)


def test_gdelt_no_articles_is_no_data(http):
    http.add("gdeltproject", {"timeline": []})
    obs, metrics = GDELTNewsConnector().run(CITY)
    assert obs.status == SourceStatus.NO_DATA and metrics == []


def test_reddit(http, creds):
    creds("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET")
    http.add("access_token", {"access_token": "tok"})
    posts = [{"data": {"upvote_ratio": 0.9, "num_comments": 3, "subreddit": "bremen"}}] * 20
    http.add("oauth.reddit.com/search", {"data": {"children": posts}})
    obs, metrics = RedditConnector().run(CITY)
    assert obs.data["posts"] == 20 and obs.data["mean_upvote_ratio"] == 0.9
    assert names(metrics)["reddit_reception"].score == 80.0


def test_open311(http):
    city = CityContext(open311_url="https://311.example.org/v2")
    http.add("requests.json", [
        {"status": "closed", "requested_datetime": "2026-09-01T10:00:00Z", "updated_datetime": "2026-09-03T10:00:00Z"},
        {"status": "closed", "requested_datetime": "2026-09-02T10:00:00Z", "updated_datetime": "2026-09-04T10:00:00Z"},
        {"status": "open", "requested_datetime": "2026-09-05T10:00:00Z"},
        {"status": "open", "requested_datetime": "2026-09-06T10:00:00Z"},
    ])
    obs, metrics = Open311Connector().run(city)
    assert obs.data["closed_share"] == 0.5 and obs.data["median_days_to_close"] == 2.0
    m = names(metrics)
    assert m["open311_resolution"].score == 50.0
    assert ValueDimension.PARTICIPATORY in m["open311_resolution"].values


# ---- E-Governance / Stakeholders -------------------------------------------


def wb_row(value, year="2024"):
    return [{"page": 1}, [{"value": value, "date": year}]]


def test_world_bank_wgi_falls_back_to_revised_codes(http):
    http.add("/indicator/VA.EST", [{"message": [{"key": "Invalid value"}]}])
    http.add("/indicator/GOV_WGI_VA.EST", wb_row(1.5))
    http.add("/indicator/RL.EST", wb_row(0.0))
    http.add("/indicator/CC.EST", wb_row(-2.5))
    http.add("/indicator/GE.EST", [{"page": 1}, []])
    http.add("/indicator/GOV_WGI_GE.EST", [{"page": 1}, None])
    obs, metrics = WorldBankGovernanceConnector().run(CITY)
    m = names(metrics)
    assert obs.data["indicators"]["wgi_voice_accountability"]["code"] == "GOV_WGI_VA.EST"
    assert m["wgi_voice_accountability"].score == 80.0
    assert m["wgi_rule_of_law"].score == 50.0
    assert m["wgi_control_of_corruption"].score == 0.0
    assert "wgi_government_effectiveness" not in m
    assert all(x.geo_level == GeoLevel.NATIONAL_PROXY for x in metrics)
    assert ValueDimension.DEMOCRATIC in m["wgi_rule_of_law"].values


def test_world_bank_fdi(http):
    http.add("BX.KLT.DINV.WD.GD.ZS", wb_row(2.0, "2023"))
    obs, metrics = WorldBankFDIConnector().run(CITY)
    assert metrics[0].score == 50.0 and metrics[0].component == SmartCityComponent.STAKEHOLDERS


def test_ckan(http):
    http.add("package_search", {"success": True, "result": {"count": 1000}}, when=lambda p: not p.get("fq"))
    http.add("package_search", {"success": True, "result": {"count": 250}}, when=lambda p: bool(p.get("fq")))
    obs, metrics = CKANOpenDataConnector().run(CITY)
    m = names(metrics)
    assert m["open_data_freshness"].score == 25.0
    assert m["open_datasets"].score == pytest.approx(66.7, abs=0.1)


def test_data_europa(http):
    http.add("data.europa.eu", {"result": {"count": 0}})
    obs, _ = DataEuropaConnector().run(CITY)
    assert obs.status == SourceStatus.NO_DATA


def test_decidim(http):
    city = CityContext(decidim_api_url="https://decidim.example.org/api")
    http.add("decidim.example.org", {"data": {"participatoryProcesses": [{"id": "1"}] * 10}}, when=lambda b: "participatoryProcesses" in b["query"])
    http.add("decidim.example.org", {"data": {"metrics": [{"name": "participants", "count": 5000}, {"name": "proposals", "count": 800}]}},
             when=lambda b: "metrics" in b["query"])
    obs, metrics = DecidimConnector().run(city)
    m = names(metrics)
    assert m["participatory_processes"].score == 50.0
    assert {"participation_participants", "participation_proposals"} <= set(m)


def test_adzuna(http, creds):
    creds("ADZUNA_APP_ID", "ADZUNA_APP_KEY")
    http.add("api.adzuna.com", {"count": 10000, "mean": 52000}, when=lambda p: "category" not in p)
    http.add("api.adzuna.com", {"count": 1000}, when=lambda p: p.get("category") == "it-jobs")
    obs, metrics = AdzunaConnector().run(CITY)
    m = names(metrics)
    assert m["tech_job_share"].score == pytest.approx(61.5, abs=0.1)
    assert ValueDimension.INNOVATIVE in m["tech_job_share"].values


# ---- Smart Tourism ---------------------------------------------------------


def test_aviationstack(http, creds):
    creds("AVIATIONSTACK_API_KEY")
    today = date.today().isoformat()
    flights = [
        {"flight_date": today, "departure": {"iata": "IST"}},
        {"flight_date": today, "departure": {"iata": "SAW"}},
        {"flight_date": today, "departure": {"iata": "XYZ", "airport": "Somewhere Intl"}},
        {"flight_date": "2000-01-01", "departure": {"iata": "LHR"}},
    ]
    http.add("aviationstack", {"data": flights})
    obs, metrics = AviationStackConnector().run(CITY)
    assert obs.data["arrivals_today"] == 3
    assert obs.data["origins"] == {"Turkey": 2, "Somewhere Intl": 1}


def test_aviationstack_api_error_is_error(http, creds):
    creds("AVIATIONSTACK_API_KEY")
    http.add("aviationstack", {"error": {"code": "usage_limit_reached", "message": "limit reached"}})
    obs, _ = AviationStackConnector().run(CITY)
    assert obs.status == SourceStatus.ERROR and "limit reached" in obs.error


def test_opensky(http, creds):
    creds("OPENSKY_CLIENT_ID", "OPENSKY_CLIENT_SECRET")
    http.add("openid-connect/token", {"access_token": "tok"})
    http.add("flights/arrival", [{"estDepartureAirport": "LTFM"}, {"estDepartureAirport": "EDDM"}, {"estDepartureAirport": "EDDM"}, {}])
    obs, metrics = OpenSkyConnector().run(CITY)
    assert obs.data["arrivals"] == 4 and obs.data["departure_airports"] == 2


def test_opensky_404_means_no_flights(http, creds):
    creds("OPENSKY_CLIENT_ID", "OPENSKY_CLIENT_SECRET")
    http.add("openid-connect/token", {"access_token": "tok"})
    response = requests.Response()
    response.status_code = 404
    http.add("flights/arrival", requests.HTTPError(response=response))
    obs, _ = OpenSkyConnector().run(CITY)
    assert obs.status == SourceStatus.NO_DATA


def test_wikimedia(http):
    http.add("pageviews", {"items": [{"views": 1000}] * 23 + [{"views": 2000}] * 7})
    obs, metrics = WikimediaPageviewsConnector().run(CITY)
    assert obs.data["last_7d_vs_prior"] == 1.0
    assert 0 < metrics[0].score < 100


def test_google_places(http, creds):
    creds("GOOGLE_PLACES_API_KEY")
    http.add("places:searchText", {"places": [
        {"displayName": {"text": "Town Hall"}, "rating": 5.0, "userRatingCount": 3000},
        {"displayName": {"text": "Schnoor"}, "rating": 4.0, "userRatingCount": 1000},
        {"displayName": {"text": "Unrated"}},
    ]})
    obs, metrics = GooglePlacesConnector().run(CITY)
    assert obs.data["review_weighted_rating"] == 4.75 and obs.data["places"] == 2


# ---- Digital Infrastructure ------------------------------------------------


def test_tomtom(http, creds):
    creds("TOMTOM_API_KEY")
    http.add("api.tomtom.com", {"flowSegmentData": {"currentSpeed": 30, "freeFlowSpeed": 40}})
    obs, metrics = TomTomTrafficConnector().run(CITY)
    assert obs.data["congestion_ratio"] == 0.25 and metrics[0].score == 75.0
    assert metrics[0].component == SmartCityComponent.DIGITAL_INFRASTRUCTURE


def test_peeringdb(http):
    http.add("/api/fac", {"data": [{}] * 2})
    http.add("/api/ix", {"data": [{"name": "BREM-IX"}]})
    obs, metrics = PeeringDBConnector().run(CITY)
    assert obs.data == {"facilities": 2, "exchanges": 1, "exchange_names": ["BREM-IX"]}


def test_opencellid(http, creds):
    creds("OPENCELLID_API_KEY")
    http.add("getInAreaSize", {"count": 200})
    obs, metrics = OpenCelliDConnector().run(CITY)
    assert obs.data["cells_in_4km2"] == 200


# ---- Sustainability --------------------------------------------------------


def test_openweather(http, creds):
    creds("OPENWEATHER_API_KEY")
    http.add("air_pollution", {"list": [{"dt": 1790000000, "main": {"aqi": 2}, "components": {"pm2_5": 5.0, "pm10": 9.0}}]})
    obs, metrics = OpenWeatherAirConnector().run(CITY)
    m = names(metrics)
    assert m["owm_aqi"].score == 75.0 and m["owm_pm25"].score == 100.0


def test_openaq(http, creds):
    creds("OPENAQ_API_KEY")
    http.add("/v3/locations/1/latest", {"results": [{"sensorsId": 11, "value": 10.0}, {"sensorsId": 12, "value": 20.0}, {"sensorsId": 13, "value": 99}]})
    http.add("/v3/locations/2/latest", {"results": [{"sensorsId": 21, "value": 20.0}, {"sensorsId": 21, "value": -1}]})
    http.add("/v3/locations", {"results": [
        {"id": 1, "name": "Bremen-Mitte", "sensors": [{"id": 11, "parameter": {"name": "pm25"}}, {"id": 12, "parameter": {"name": "no2"}}, {"id": 13, "parameter": {"name": "o3"}}]},
        {"id": 2, "name": "Bremen-Ost", "sensors": [{"id": 21, "parameter": {"name": "pm25"}}]},
        {"id": 3, "name": "Temp only", "sensors": [{"id": 31, "parameter": {"name": "temperature"}}]},
    ]})
    obs, metrics = OpenAQConnector().run(CITY)
    assert obs.data["pm25"] == 15.0 and obs.data["no2"] == 20.0
    assert obs.data["stations"] == ["Bremen-Mitte", "Bremen-Ost"]


def test_aqicn(http, creds):
    creds("AQICN_TOKEN")
    http.add("api.waqi.info", {"status": "ok", "data": {"aqi": 50, "city": {"name": "Bremen"}, "time": {"iso": "x"}}})
    obs, metrics = AQICNConnector().run(CITY)
    assert metrics[0].score == 75.0


def test_aqicn_no_reading(http, creds):
    creds("AQICN_TOKEN")
    http.add("api.waqi.info", {"status": "ok", "data": {"aqi": "-"}})
    obs, _ = AQICNConnector().run(CITY)
    assert obs.status == SourceStatus.NO_DATA


# ---- Curated and benchmarks ------------------------------------------------


def test_curated_metrics_are_labelled_and_down_weighted(http):
    obs, metrics = CuratedDataConnector().run(CITY)
    assert metrics, "manual_data.json ships with the repo"
    for m in metrics:
        assert m.evidence_type == EvidenceType.CURATED
        assert m.weight <= 0.5
    assert {m.component for m in metrics} >= {SmartCityComponent.TOURISM, SmartCityComponent.STAKEHOLDERS}


def test_shipped_benchmarks_are_all_unfilled(http):
    obs, metrics = BenchmarksConnector().run(CITY)
    assert obs.status == SourceStatus.NO_DATA and metrics == []


def test_benchmark_requires_value_year_and_citation():
    entry = {"value": 70, "year": "2025", "citation": None, "scale": {"type": "score", "min": 0, "max": 100}}
    assert not is_filled(entry)
    entry["citation"] = "CPI 2025, transparency.org"
    assert is_filled(entry) and benchmark_score(entry) == 70.0
    rank = {"value": 1, "year": "2025", "citation": "x", "scale": {"type": "rank", "total": None}}
    assert not is_filled(rank)
    rank["scale"]["total"] = 101
    assert is_filled(rank) and benchmark_score(rank) == 100.0
