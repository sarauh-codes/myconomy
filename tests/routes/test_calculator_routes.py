"""Route and integration tests for the purchasing power calculator.

CPI values are seeded through the real refresh path with a stubbed upstream.
"""

from datetime import date, datetime

from app.services.data_service import refresh_indicator
from app.services.opendosm_client import UpstreamUnavailable
from tests.helpers import StubClient, cpi_row, envelope

NOW = datetime(2026, 11, 5, 9, 0)


def seed_rows(app, rows):
    outcome = refresh_indicator("cpi_headline", StubClient(envelope(rows)), now=NOW)
    assert outcome.ok, outcome.message


def seed_default(app):
    # Jan 2020 = 126.5 and Sep 2026 = 137.6, with Jun 2020 missing and Feb 2020 marked missing.
    seed_rows(
        app,
        [
            cpi_row("2026-09-01", 137.6),
            cpi_row("2020-02-01", None),
            cpi_row("2020-01-01", 126.5),
        ],
    )


def test_empty_form_is_shown_without_errors(client):
    response = client.get("/calculator")
    assert response.status_code == 200
    assert b"Purchasing power calculator" in response.data
    assert b"Please check the form" not in response.data


def test_valid_calculation_shows_result_formula_and_source(app, client):
    seed_default(app)
    response = client.get("/calculator?amount=100&source=2020-01&target=2026-09")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "RM 100.00" in html
    assert "RM 108.77" in html
    assert "Formula: equivalent amount = input amount × (target CPI ÷ starting CPI)" in html
    assert "Ratio (target ÷ starting)" in html
    assert "1.0877" in html
    assert "+8.8%" in html  # 108.77 vs 100 (rounded to one decimal)
    assert "Reference period 2026-09" in html
    assert "developer.data.gov.my" in html


def test_direction_is_stated_as_starting_to_target(app, client):
    seed_default(app)
    html = client.get("/calculator?amount=100&source=2026-09&target=2020-01").get_data(as_text=True)
    assert "RM 100.00" in html
    assert "in 2026-09" in html
    assert "equivalent to" in html
    assert "RM 91.93" in html  # falls when moving back to the lower CPI month


def test_same_month_returns_the_input_amount(app, client):
    seed_default(app)
    html = client.get("/calculator?amount=250.50&source=2026-09&target=2026-09").get_data(as_text=True)
    assert "RM 250.50" in html
    assert "+0.0%" in html


def test_unavailable_month_is_reported_with_stored_range(app, client):
    seed_default(app)
    response = client.get("/calculator?amount=100&source=1999-01&target=2026-09")
    html = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "No CPI value is stored for 1999-01" in html
    assert "Stored months run from 2020-01 to 2026-09" in html


def test_missing_cpi_value_is_not_estimated(app, client):
    seed_default(app)
    response = client.get("/calculator?amount=100&source=2020-02&target=2026-09")
    assert response.status_code == 400
    assert b"marked as missing by the source" in response.data
    assert b"RM 108.77" not in response.data


def test_negative_amount_is_rejected_with_message(client):
    response = client.get("/calculator?amount=-5&source=2020-01&target=2026-09")
    assert response.status_code == 400
    assert b"zero or positive" in response.data
    assert b'aria-invalid="true"' in response.data


def test_non_numeric_amount_and_bad_period_each_show_a_message(client):
    response = client.get("/calculator?amount=abc&source=2020-13&target=")
    html = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "Enter a number" in html
    assert "Use the format YYYY-MM" in html
    assert "Choose a target month." in html


def test_error_summary_links_to_each_field(client):
    html = client.get("/calculator?amount=-1&source=&target=").get_data(as_text=True)
    assert 'href="#amount"' in html
    assert 'href="#source"' in html
    assert 'href="#target"' in html


def test_no_data_yet_gives_a_clear_message(client):
    response = client.get("/calculator?amount=100&source=2020-01&target=2026-09")
    assert response.status_code == 400
    assert b"No CPI values are stored yet. Run the data refresh first." in response.data


def test_stale_data_is_labelled_on_result(app, client):
    seed_default(app)
    refresh_indicator("cpi_headline", StubClient(UpstreamUnavailable("down")), now=NOW)
    html = client.get("/calculator?amount=100&source=2020-01&target=2026-09").get_data(as_text=True)
    assert "Showing the last successful data" in html
    assert "notice-error" in html
