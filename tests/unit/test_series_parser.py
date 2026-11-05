"""Unit tests for series validation. Each invalid shape must be rejected, not partly saved."""

from decimal import Decimal

import pytest

from app.services.dataset_registry import INDICATORS
from app.services.opendosm_client import MalformedResponse
from app.services.series_parser import parse_meta, parse_observations
from tests.helpers import cpi_row, envelope

SPEC = INDICATORS["cpi_headline"]


def test_valid_rows_are_parsed_and_sorted_oldest_first():
    data = envelope([cpi_row("2026-09-01", 137.6), cpi_row("2026-08-01", 137.5)])
    observations = parse_observations(data, SPEC)
    assert [o.reference_period.isoformat() for o in observations] == ["2026-08-01", "2026-09-01"]
    assert observations[-1].value == Decimal("137.6")


def test_empty_data_list_is_returned_as_empty_not_error():
    assert parse_observations(envelope([]), SPEC) == []


def test_null_value_is_kept_as_missing():
    observations = parse_observations(envelope([cpi_row("2026-09-01", None)]), SPEC)
    assert observations[0].value is None


@pytest.mark.parametrize(
    "row, reason",
    [
        ({"date": "2026-09-01", "division": "overall"}, "missing the 'index' field"),
        ({"index": 1.0, "division": "overall"}, "missing the 'date' field"),
        ({"date": "2026-09-01", "index": 1.0}, "missing the 'division' field"),
        (cpi_row("2026-09-01", 137.6, division="01"), "expected 'overall'"),
        (cpi_row("2026-09-15", 137.6), "not on the first of the month"),
        (cpi_row("2026-13-01", 137.6), "invalid date"),
        (cpi_row("2026-09-01", "137.6"), "non-numeric value"),
        (cpi_row("2026-09-01", True), "non-numeric value"),
        (cpi_row("2026-09-01", float("nan")), "non-finite value"),
        (cpi_row("2026-09-01", -5.0), "outside the plausible range"),
        (cpi_row("2026-09-01", 0), "outside the plausible range"),
        ("not-an-object", "is not an object"),
    ],
)
def test_invalid_rows_are_rejected(row, reason):
    with pytest.raises(MalformedResponse, match=reason):
        parse_observations(envelope([row]), SPEC)


def test_duplicate_period_is_rejected():
    rows = [cpi_row("2026-09-01", 137.6), cpi_row("2026-09-01", 137.7)]
    with pytest.raises(MalformedResponse, match="Duplicate period"):
        parse_observations(envelope(rows), SPEC)


def test_data_field_must_be_a_list():
    with pytest.raises(MalformedResponse):
        parse_observations({"meta": {}, "data": "oops"}, SPEC)


def test_meta_is_parsed_into_typed_values():
    meta = parse_meta(envelope([], data_as_of="2026-09"))
    assert meta.data_as_of == "2026-09"
    assert meta.update_frequency == "MONTHLY"
    assert meta.last_updated.isoformat() == "2026-10-19T13:12:00"
    assert meta.next_update.isoformat() == "2026-11-19T12:30:00"


def test_missing_meta_fields_become_none():
    meta = parse_meta({"meta": {}, "data": []})
    assert meta.data_as_of is None
    assert meta.last_updated is None
