"""Route tests for the Learn & understand pages."""

from datetime import datetime

from app.services.calculator_service import FORMULA_TEXT
from app.services.data_service import refresh_indicator
from tests.helpers import StubClient, cpi_row, envelope

NOW = datetime(2026, 11, 5, 9, 0)
TOPIC_SLUGS = ["cpi", "inflation", "purchasing-power"]


def seed_rows(app, rows):
    outcome = refresh_indicator("cpi_headline", StubClient(envelope(rows)), now=NOW)
    assert outcome.ok, outcome.message


def test_index_lists_every_topic(client):
    response = client.get("/learn")
    assert response.status_code == 200
    for slug in TOPIC_SLUGS:
        assert f'href="/learn/{slug}"'.encode() in response.data


def test_every_topic_page_loads_with_required_parts(client):
    for slug in TOPIC_SLUGS:
        response = client.get(f"/learn/{slug}")
        html = response.get_data(as_text=True)
        assert response.status_code == 200, slug
        assert "<h1" in html
        assert "Illustrative" in html  # illustrative examples are labelled
        assert "Official" in html  # official examples are labelled
        assert "Invented numbers for explanation only." in html
        assert "developer.data.gov.my" in html  # links to the official source
        assert "Sources" in html


def test_unknown_topic_is_404(client):
    assert client.get("/learn/unknown-topic").status_code == 404


def test_purchasing_power_explanation_uses_the_calculator_formula(client):
    # The explanation and the calculator share one formula constant (LEARN-03).
    learn_html = client.get("/learn/purchasing-power").get_data(as_text=True)
    assert FORMULA_TEXT in learn_html


def test_calculator_result_shows_the_shared_formula(app, client):
    seed_rows(app, [cpi_row("2026-09-01", 137.6), cpi_row("2020-01-01", 126.5)])
    html = client.get("/calculator?amount=100&source=2020-01&target=2026-09").get_data(as_text=True)
    assert FORMULA_TEXT in html


def test_official_examples_show_unavailable_message_without_data(client):
    cpi = client.get("/learn/cpi").get_data(as_text=True)
    assert "Not available right now" in cpi
    assert "No data has been retrieved yet." in cpi

    purchasing = client.get("/learn/purchasing-power").get_data(as_text=True)
    assert "Not available right now" in purchasing


def test_official_examples_use_stored_data_when_available(app, client):
    seed_rows(
        app,
        [
            cpi_row("2026-09-01", 137.6),
            cpi_row("2025-09-01", 120.0),
            cpi_row("2020-01-01", 126.5),
        ],
    )

    cpi = client.get("/learn/cpi").get_data(as_text=True)
    assert "The latest stored headline CPI is 137.6, for 2026-09." in cpi

    inflation = client.get("/learn/inflation").get_data(as_text=True)
    assert "+14.7 per cent, compared with 2025-09" in inflation

    purchasing = client.get("/learn/purchasing-power").get_data(as_text=True)
    assert "RM 100.00 in 2020-01 is equivalent to RM 108.77 in 2026-09" in purchasing


def test_inflation_example_is_unavailable_without_a_year_earlier(app, client):
    seed_rows(app, [cpi_row("2026-09-01", 137.6)])
    html = client.get("/learn/inflation").get_data(as_text=True)
    assert "Not enough stored months to compare with a year earlier." in html


def test_illustrative_examples_never_use_stored_figures(app, client):
    seed_rows(app, [cpi_row("2026-09-01", 137.6), cpi_row("2020-01-01", 126.5)])
    for slug in TOPIC_SLUGS:
        html = client.get(f"/learn/{slug}").get_data(as_text=True)
        illustrative_block = html.split('example-illustrative')[1].split('example-official')[0]
        assert "137.6" not in illustrative_block
        assert "126.5" not in illustrative_block
