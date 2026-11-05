"""Quick stats widget: fresh, stale, and unavailable states, accessibility, and cache-only reads."""

from datetime import datetime

import pytest

from app.services.data_service import refresh_indicator
from app.services.opendosm_client import OpenDOSMClient, UpstreamUnavailable
from tests.helpers import StubClient, cpi_row, envelope

NOW = datetime(2026, 11, 5, 9, 0)


def seed_cpi(app, rows=None, now=NOW):
    rows = rows or [cpi_row("2026-09-01", 137.6), cpi_row("2020-01-01", 126.5)]
    outcome = refresh_indicator("cpi_headline", StubClient(envelope(rows)), now=now)
    assert outcome.ok, outcome.message


# WID-01: fresh data shows value, indicator, and reference period


def test_fresh_widget_shows_value_name_and_reference_period(app, client):
    seed_cpi(app)
    response = client.get("/widget/cpi_headline")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Consumer Price Index (headline)" in html
    assert "137.6" in html
    assert "Reference period: <strong>2026-09</strong>" in html
    assert "Current" in html
    assert "index points (base year not confirmed)" in html


def test_widget_shows_retrieval_time_separately_from_reference_period(app, client):
    seed_cpi(app)
    html = client.get("/widget/cpi_headline").get_data(as_text=True)
    assert "Retrieved: 2026-11-05 09:00 UTC" in html


def test_widget_links_to_details_and_source(app, client):
    seed_cpi(app)
    html = client.get("/widget/cpi_headline").get_data(as_text=True)
    assert 'href="/dashboard?indicator=cpi_headline"' in html
    assert 'href="https://developer.data.gov.my/static-api/opendosm"' in html


# WID-02: stale data is labelled as stale


def test_widget_is_stale_after_a_failed_refresh(app, client):
    seed_cpi(app)
    refresh_indicator("cpi_headline", StubClient(UpstreamUnavailable("down")), now=NOW)
    html = client.get("/widget/cpi_headline").get_data(as_text=True)
    assert "quick-stat-stale" in html
    assert "Stale" in html
    assert "Showing the last successful data" in html
    assert "137.6" in html  # the last good value is kept


# WID-03: no data shows a compact unavailable state


def test_widget_without_data_shows_unavailable_state(client):
    response = client.get("/widget/cpi_headline")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Unavailable" in html
    assert "No data has been retrieved yet." in html
    assert html.count('class="quick-stat-value data">Not available</p>') == 1


# WID-04: content stays usable and accessible


def test_widget_heading_is_linked_to_the_article(client):
    html = client.get("/widget/unemployment_rate").get_data(as_text=True)
    assert 'aria-labelledby="qs-unemployment_rate"' in html
    assert 'id="qs-unemployment_rate"' in html


def test_status_is_stated_in_words_not_only_colour(app, client):
    seed_cpi(app)
    html = client.get("/widget/cpi_headline").get_data(as_text=True)
    assert '<span class="tag status-fresh">Current</span>' in html


def test_links_have_descriptive_text(client):
    html = client.get("/widget/cpi_headline").get_data(as_text=True)
    assert "Details<span" in html and "Source<span" in html
    assert "visually-hidden" in html


def test_widget_fragment_declares_language_and_viewport(client):
    html = client.get("/widget/cpi_headline").get_data(as_text=True)
    assert 'lang="en"' in html
    assert 'name="viewport"' in html


# Formatting


def test_rate_indicator_shows_percent_sign(app, client):
    from tests.helpers import envelope as env

    body = env([{"date": "2026-08-01", "u_rate": 2.9}])
    body["meta"]["update_frequency"] = "MONTHLY"
    refresh_indicator("unemployment_rate", StubClient(body), now=NOW)
    html = client.get("/widget/unemployment_rate").get_data(as_text=True)
    assert "2.9%" in html
    assert "2026-08" in html


def test_level_indicator_uses_thousands_separator(app, client):
    body = envelope([{"date": "2026-04-01", "series": "abs", "value": 445896.454}])
    body["meta"]["update_frequency"] = "QUARTERLY"
    body["meta"]["data_as_of"] = "2026-Q2"
    refresh_indicator("gdp_real_level", StubClient(body), now=NOW)
    html = client.get("/widget/gdp_real_level").get_data(as_text=True)
    assert "445,896.5" in html
    assert "2026-Q2" in html


# Cache-only reads


def test_widget_never_calls_the_provider(app, client, monkeypatch):
    seed_cpi(app)

    def forbidden(self, *args, **kwargs):
        raise AssertionError("the widget must not call OpenDOSM")

    monkeypatch.setattr(OpenDOSMClient, "fetch_series", forbidden)
    assert client.get("/widget/cpi_headline").status_code == 200
    assert client.get("/api/indicators/cpi_headline/latest").status_code == 200
    assert client.get("/").status_code == 200


# Endpoints


def test_unknown_widget_is_404(client):
    assert client.get("/widget/nope").status_code == 404


def test_latest_json_contract(app, client):
    seed_cpi(app)
    body = client.get("/api/indicators/cpi_headline/latest").get_json()
    assert body["indicator"] == "cpi_headline"
    assert body["value"] == "137.6"
    assert body["reference_period"] == "2026-09"
    assert body["status"] == "fresh"
    assert body["status_text"] == "Current"
    assert body["details_url"] == "/dashboard?indicator=cpi_headline"


def test_latest_json_unknown_indicator_is_404(client):
    response = client.get("/api/indicators/nope/latest")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Unknown indicator."}


def test_home_page_shows_three_quick_stats(app, client):
    seed_cpi(app)
    html = client.get("/").get_data(as_text=True)
    assert "Latest figures" in html
    assert html.count('class="quick-stat ') == 3
    assert "137.6" in html


@pytest.mark.parametrize("path", ["/widget/cpi_headline", "/api/indicators/cpi_headline/latest"])
def test_widget_endpoints_are_public(client, path):
    assert client.get(path).status_code == 200
