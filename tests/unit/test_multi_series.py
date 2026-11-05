"""Unit tests for multi-series datasets, rate bounds, and quarterly periods. No database."""

from dataclasses import replace
from decimal import Decimal

import pytest

from app.services.dataset_registry import INDICATORS, format_period
from app.services.opendosm_client import MalformedResponse
from app.services.series_parser import parse_observations
from tests.helpers import envelope

GDP_LEVEL = INDICATORS["gdp_real_level"]
GDP_GROWTH = INDICATORS["gdp_growth_yoy"]
UNEMPLOYMENT = INDICATORS["unemployment_rate"]
CPI = INDICATORS["cpi_headline"]


def gdp_rows():
    return [
        {"date": "2025-01-01", "series": "abs", "value": 430000.0},
        {"date": "2025-01-01", "series": "growth_yoy", "value": 5.1},
        {"date": "2025-01-01", "series": "growth_qoq", "value": 1.2},
        {"date": "2025-04-01", "series": "abs", "value": 436000.5},
        {"date": "2025-04-01", "series": "growth_yoy", "value": -0.4},
    ]


def test_unfiltered_dataset_yields_only_the_requested_series():
    level = parse_observations(envelope(gdp_rows()), GDP_LEVEL)
    growth = parse_observations(envelope(gdp_rows()), GDP_GROWTH)
    assert [o.value for o in level] == [Decimal("430000.0"), Decimal("436000.5")]
    assert [o.value for o in growth] == [Decimal("5.1"), Decimal("-0.4")]


def test_negative_growth_is_allowed():
    observations = parse_observations(envelope([{"date": "2025-04-01", "series": "growth_yoy", "value": -16.9}]), GDP_GROWTH)
    assert observations[0].value == Decimal("-16.9")


def test_missing_series_field_is_rejected():
    rows = [{"date": "2025-01-01", "value": 1.0}]
    with pytest.raises(MalformedResponse, match="'series'"):
        parse_observations(envelope(rows), GDP_LEVEL)


def test_server_filtered_response_with_a_mismatched_row_is_rejected():
    # CPI is fetched with overall@division, so any other division means the filter was ignored.
    rows = [{"date": "2026-09-01", "index": 137.6, "division": "01"}]
    with pytest.raises(MalformedResponse, match="expected 'overall'"):
        parse_observations(envelope(rows), CPI)


def test_unemployment_zero_is_allowed_but_negative_is_not():
    observations = parse_observations(envelope([{"date": "2026-08-01", "u_rate": 0.0}]), UNEMPLOYMENT)
    assert observations[0].value == Decimal("0.0")
    with pytest.raises(MalformedResponse, match="outside the plausible range"):
        parse_observations(envelope([{"date": "2026-08-01", "u_rate": -0.1}]), UNEMPLOYMENT)


def test_quarter_start_dates_are_accepted():
    rows = [{"date": "2026-04-01", "series": "abs", "value": 445896.454}]
    observations = parse_observations(envelope(rows), GDP_LEVEL)
    assert observations[0].reference_period.month == 4


def test_mid_quarter_date_is_rejected():
    rows = [{"date": "2026-05-15", "series": "abs", "value": 1.0}]
    with pytest.raises(MalformedResponse, match="first of the month"):
        parse_observations(envelope(rows), GDP_LEVEL)


def test_format_period_labels():
    from datetime import date

    assert format_period(date(2026, 9, 1), "MONTHLY") == "2026-09"
    assert format_period(date(2026, 4, 1), "QUARTERLY") == "2026-Q2"
    assert format_period(date(2026, 10, 1), "QUARTERLY") == "2026-Q4"
    assert format_period(date(2023, 1, 1), "YEARLY") == "2023"


def test_every_registered_indicator_is_internally_consistent():
    for spec in INDICATORS.values():
        assert spec.geography
        assert spec.unit
        assert spec.periods_per_year in (1, 4, 12)
        assert spec.value_kind in ("index", "level", "rate")
        if spec.dimension_field:
            assert spec.dimension_value
        if spec.filter_expression:
            assert "@" in spec.filter_expression
        assert spec.shows_changes == (spec.value_kind in ("index", "level"))


def test_indicators_from_the_same_dataset_share_a_fetch_key_only_when_unfiltered():
    assert GDP_LEVEL.fetch_key == GDP_GROWTH.fetch_key == ("gdp_qtr_real", None)
    assert CPI.fetch_key != UNEMPLOYMENT.fetch_key
    assert replace(CPI, filter_expression=None).fetch_key == ("cpi_headline", None)
