"""Integration tests: refresh and snapshot logic against an in-memory database.

The upstream is stubbed, so these tests never touch the network.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from app.extensions import db
from app.models import CacheEntry, DataPoint, Indicator
from app.services.data_service import (
    SNAPSHOT_FRESH,
    SNAPSHOT_STALE,
    SNAPSHOT_UNAVAILABLE,
    get_snapshot,
    refresh_indicator,
)
from app.services.opendosm_client import MalformedResponse, UpstreamUnavailable
from tests.helpers import StubClient, cpi_row, envelope

CODE = "cpi_headline"
NOW = datetime(2026, 11, 5, 9, 0, 0)

GOOD_ROWS = [
    cpi_row("2026-09-01", 137.6),
    cpi_row("2026-08-01", 137.5),
    cpi_row("2026-07-01", 137.2),
]


def point_count() -> int:
    indicator = Indicator.query.filter_by(code=CODE).first()
    return DataPoint.query.filter_by(indicator_id=indicator.id).count() if indicator else 0


def test_successful_refresh_stores_points_and_snapshot_is_fresh(app):
    outcome = refresh_indicator(CODE, StubClient(envelope(GOOD_ROWS)), now=NOW)

    assert outcome.ok is True
    assert point_count() == 3
    snapshot = get_snapshot(CODE, now=NOW + timedelta(hours=1))
    assert snapshot.status == SNAPSHOT_FRESH
    assert snapshot.latest_period.isoformat() == "2026-09-01"
    assert snapshot.latest_value == Decimal("137.6")
    assert snapshot.data_as_of == "2026-09"
    assert snapshot.retrieved_at == NOW


def test_refresh_is_idempotent_and_does_not_duplicate_rows(app):
    refresh_indicator(CODE, StubClient(envelope(GOOD_ROWS)), now=NOW)
    refresh_indicator(CODE, StubClient(envelope(GOOD_ROWS)), now=NOW + timedelta(hours=13))
    assert point_count() == 3


def test_failed_refresh_keeps_previous_data_and_marks_stale(app):
    refresh_indicator(CODE, StubClient(envelope(GOOD_ROWS)), now=NOW)

    outcome = refresh_indicator(
        CODE, StubClient(UpstreamUnavailable("The statistics service did not respond in time.")), now=NOW + timedelta(hours=2)
    )

    assert outcome.ok is False
    assert point_count() == 3  # nothing was erased
    snapshot = get_snapshot(CODE, now=NOW + timedelta(hours=2))
    assert snapshot.status == SNAPSHOT_STALE
    assert snapshot.latest_value == Decimal("137.6")
    assert "did not respond in time" in snapshot.status_message
    assert snapshot.retrieved_at == NOW  # the last successful retrieval time is kept


def test_empty_response_keeps_previous_data(app):
    refresh_indicator(CODE, StubClient(envelope(GOOD_ROWS)), now=NOW)

    outcome = refresh_indicator(CODE, StubClient(envelope([])), now=NOW + timedelta(hours=2))

    assert outcome.ok is False
    assert "no records" in outcome.message
    assert point_count() == 3
    assert get_snapshot(CODE, now=NOW + timedelta(hours=2)).status == SNAPSHOT_STALE


def test_malformed_response_writes_nothing(app):
    refresh_indicator(CODE, StubClient(envelope(GOOD_ROWS)), now=NOW)
    changed = [cpi_row("2026-09-01", 999.9), cpi_row("2026-08-01", "bad")]

    outcome = refresh_indicator(CODE, StubClient(envelope(changed)), now=NOW + timedelta(hours=2))

    assert outcome.ok is False
    snapshot = get_snapshot(CODE, now=NOW + timedelta(hours=2))
    assert snapshot.latest_value == Decimal("137.6")  # the bad batch was not applied
    assert point_count() == 3
    assert "non-numeric" in snapshot.status_message


def test_first_failure_gives_unavailable_snapshot(app):
    outcome = refresh_indicator(CODE, StubClient(MalformedResponse("broken")), now=NOW)

    assert outcome.ok is False
    snapshot = get_snapshot(CODE, now=NOW)
    assert snapshot.status == SNAPSHOT_UNAVAILABLE
    assert snapshot.latest_value is None
    assert snapshot.observation_count == 0


def test_snapshot_becomes_stale_after_its_freshness_window(app):
    refresh_indicator(CODE, StubClient(envelope(GOOD_ROWS)), now=NOW)

    assert get_snapshot(CODE, now=NOW + timedelta(hours=11)).status == SNAPSHOT_FRESH
    assert get_snapshot(CODE, now=NOW + timedelta(hours=13)).status == SNAPSHOT_STALE


def test_latest_value_skips_missing_observations(app):
    rows = [cpi_row("2026-09-01", None), cpi_row("2026-08-01", 137.5)]
    refresh_indicator(CODE, StubClient(envelope(rows)), now=NOW)

    snapshot = get_snapshot(CODE, now=NOW)
    assert snapshot.latest_period.isoformat() == "2026-08-01"
    assert snapshot.latest_value == Decimal("137.5")


def test_indicator_metadata_is_synced_from_registry(app):
    refresh_indicator(CODE, StubClient(envelope(GOOD_ROWS)), now=NOW)
    indicator = Indicator.query.filter_by(code=CODE).one()
    assert indicator.dataset_id == "cpi_headline"
    assert indicator.frequency == "MONTHLY"
    assert indicator.source_url.startswith("https://developer.data.gov.my/")
    assert CacheEntry.query.filter_by(cache_key="indicator:cpi_headline").count() == 1
