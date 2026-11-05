"""Route tests for the economic dashboard and its series endpoint.

Data is seeded through the real refresh path with a stubbed upstream, so these
tests cover the database, calculations, and templates together.
"""

from datetime import datetime

from app.services.data_service import refresh_indicator
from app.services.dashboard_service import shift_months
from app.services.opendosm_client import UpstreamUnavailable
from tests.helpers import StubClient, cpi_row, envelope

NOW = datetime(2026, 11, 5, 9, 0)


def seed(app, values, *, end_period=(2026, 9)):
    """Store consecutive monthly values ending at end_period. None means missing."""
    from datetime import date

    end = date(*end_period, 1)
    rows = []
    for offset, value in enumerate(reversed(values)):
        period = shift_months(end, -offset)
        rows.append(cpi_row(period.isoformat(), value))
    outcome = refresh_indicator("cpi_headline", StubClient(envelope(rows)), now=NOW)
    assert outcome.ok, outcome.message


def test_dashboard_with_no_data_shows_empty_state(client):
    response = client.get("/dashboard")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Unavailable" in html
    assert "No data has been retrieved yet" in html
    assert "Not available" in html  # latest value placeholder


def test_dashboard_shows_latest_value_changes_period_and_source(app, client):
    # 13 months: Sep 2025 = 100.0 rising by 1.0 each month, ending at 112.0 in Sep 2026.
    seed(app, [100.0 + i for i in range(13)])

    response = client.get("/dashboard")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "112.0" in html  # latest value
    assert "+12.0%" in html  # change over 12 months (vs Sep 2025 = 100.0)
    assert "Compared with 2025-09" in html
    assert "+0.9%" in html  # change from last month (vs Aug 2026 = 111.0)
    assert 'id="chart"' in html
    assert "developer.data.gov.my" in html
    assert "View data table" in html
    assert "2026-09" in html  # reference period, shown separately from retrieval time
    assert "2026-11-05 09:00" in html  # retrieval time


def test_dashboard_data_table_lists_values_newest_first(app, client):
    seed(app, [100.0, 101.0, 102.0])
    html = client.get("/dashboard?range=1y").get_data(as_text=True)
    assert html.index("<td>2026-09</td>") < html.index("<td>2026-08</td>") < html.index("<td>2026-07</td>")


def test_missing_value_shows_as_not_available_and_is_not_estimated(app, client):
    seed(app, [100.0, None, 102.0])  # Jul 2026 = 100, Aug 2026 missing, Sep 2026 = 102
    response = client.get("/dashboard?range=1y")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "102.0" in html
    # The previous month is missing, so its change is shown as unavailable, not estimated.
    assert "Compared with 2026-08" in html
    assert "Not available" in html
    assert "+2.0%" not in html and "+1.0%" not in html


def test_unknown_indicator_is_a_400_message_not_a_server_error(client):
    response = client.get("/dashboard?indicator=bogus")
    assert response.status_code == 400
    assert b"That indicator is not available" in response.data


def test_unknown_range_is_a_400_message_not_a_server_error(client):
    response = client.get("/dashboard?range=forever")
    assert response.status_code == 400
    assert b"That time range is not available" in response.data


def test_series_endpoint_returns_ordered_points_and_metadata(app, client):
    seed(app, [100.0 + i for i in range(13)])

    response = client.get("/api/indicators/cpi_headline/series?range=5y")
    body = response.get_json()
    assert response.status_code == 200
    assert body["indicator"] == "cpi_headline"
    assert body["range"] == "5y"
    assert body["status"] == "fresh"
    assert body["data_as_of"] == "2026-09"
    assert body["retrieved_at"] == "2026-11-05T09:00:00Z"
    periods = [p["period"] for p in body["points"]]
    assert periods == sorted(periods)
    assert body["points"][-1] == {"period": "2026-09-01", "value": 112.0}


def test_series_endpoint_range_limits_points(app, client):
    seed(app, [100.0 + i for i in range(20)])
    body = client.get("/api/indicators/cpi_headline/series?range=1y").get_json()
    assert len(body["points"]) == 12


def test_series_endpoint_reports_missing_values_as_null(app, client):
    seed(app, [100.0, None, 102.0])
    body = client.get("/api/indicators/cpi_headline/series?range=1y").get_json()
    assert [p["value"] for p in body["points"]] == [100.0, None, 102.0]


def test_series_endpoint_unknown_indicator_is_404(client):
    response = client.get("/api/indicators/nope/series")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Unknown indicator."}


def test_series_endpoint_invalid_range_is_400(client):
    response = client.get("/api/indicators/cpi_headline/series?range=forever")
    assert response.status_code == 400


def test_stale_snapshot_is_labelled_on_dashboard(app, client):
    seed(app, [100.0, 101.0])
    refresh_indicator("cpi_headline", StubClient(UpstreamUnavailable("down")), now=NOW)

    html = client.get("/dashboard").get_data(as_text=True)
    assert "Stale" in html
    assert "Showing the last successful data" in html
