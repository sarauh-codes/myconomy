"""Route tests for the read-only data status page."""

from datetime import datetime

from app.services.data_service import refresh_indicator
from tests.helpers import StubClient, cpi_row, envelope


def test_status_page_with_no_data_says_unavailable(client):
    response = client.get("/data-status")
    assert response.status_code == 200
    assert b"Consumer Price Index" in response.data
    assert b"Unavailable" in response.data
    assert b"No data has been retrieved yet" in response.data


def test_status_page_shows_value_period_source_and_retrieval_time(app, client):
    refresh_indicator(
        "cpi_headline",
        StubClient(envelope([cpi_row("2026-09-01", 137.6)])),
        now=datetime(2026, 11, 5, 9, 0),
    )

    response = client.get("/data-status")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "137.6" in html
    assert "2026-09" in html  # reference period
    assert "2026-11-05 09:00" in html  # retrieval time, labelled separately
    assert "developer.data.gov.my" in html  # source link
    assert "Retrieved by Myconomy (UTC)" in html


def test_status_page_is_read_only(client):
    assert client.post("/data-status").status_code == 405
