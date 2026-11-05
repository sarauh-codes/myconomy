"""Route tests for the multi-indicator explorer and indicator-specific dashboard views."""

from datetime import datetime

from app.services.data_service import refresh_indicator
from tests.helpers import StubClient, envelope

NOW = datetime(2026, 11, 5, 9, 0)


def test_explorer_lists_every_registered_indicator_with_metadata(client):
    response = client.get("/explore")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    for name in [
        "Consumer Price Index (headline)",
        "Real gross domestic product (level)",
        "Real GDP growth, year on year",
        "Unemployment rate",
    ]:
        assert name in html
    assert html.count("Malaysia (national)") == 4
    assert "per cent of the labour force" in html
    assert "No values stored yet" in html  # nothing refreshed in this test


def test_explorer_says_indicators_are_not_compared(client):
    html = client.get("/explore").get_data(as_text=True)
    assert "are not compared with each other" in html


def test_explorer_links_each_indicator_to_its_dashboard_view(client):
    html = client.get("/explore").get_data(as_text=True)
    assert 'href="/dashboard?indicator=unemployment_rate"' in html


def test_rate_indicator_dashboard_hides_change_figures(app, client):
    body = envelope([{"date": "2026-08-01", "u_rate": 3.5}, {"date": "2025-08-01", "u_rate": 3.0}])
    body["meta"]["update_frequency"] = "MONTHLY"
    refresh_indicator("unemployment_rate", StubClient(body), now=NOW)

    html = client.get("/dashboard?indicator=unemployment_rate").get_data(as_text=True)
    assert "This series is already a rate" in html
    assert "Change over 12 months" not in html
    assert "3.5" in html


def test_quarterly_dashboard_shows_quarter_labels(app, client):
    body = envelope(
        [
            {"date": "2026-04-01", "series": "abs", "value": 445896.454},
            {"date": "2026-01-01", "series": "abs", "value": 437670.264},
        ]
    )
    body["meta"]["data_as_of"] = "2026-Q2"
    body["meta"]["update_frequency"] = "QUARTERLY"
    refresh_indicator("gdp_real_level", StubClient(body), now=NOW)

    html = client.get("/dashboard?indicator=gdp_real_level&range=1y").get_data(as_text=True)
    assert "2026-Q2" in html
    assert "2026-Q1" in html
    assert "Change from last quarter" in html


def test_dashboard_rejects_unknown_indicator_from_new_list(client):
    response = client.get("/dashboard?indicator=population")
    assert response.status_code == 400

