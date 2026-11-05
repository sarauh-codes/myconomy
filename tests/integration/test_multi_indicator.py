"""Integration tests: several indicators from one dataset, freshness from the provider's schedule."""

from datetime import datetime, timedelta
from decimal import Decimal

from app.models import DataPoint, Indicator
from app.services.data_service import SNAPSHOT_FRESH, SNAPSHOT_STALE, get_snapshot, refresh_indicator
from tests.helpers import StubClient, envelope

NOW = datetime(2026, 11, 5, 9, 0)


def gdp_envelope(next_update: str = "2026-11-18 12:00"):
    body = envelope(
        [
            {"date": "2026-04-01", "series": "abs", "value": 445896.454},
            {"date": "2026-04-01", "series": "growth_yoy", "value": 6.0},
            {"date": "2026-01-01", "series": "abs", "value": 437670.264},
            {"date": "2026-01-01", "series": "growth_yoy", "value": 5.4},
        ]
    )
    body["meta"]["data_as_of"] = "2026-Q2"
    body["meta"]["update_frequency"] = "QUARTERLY"
    body["meta"]["next_update"] = next_update
    return body


def stored(code: str, division: str) -> int:
    indicator = Indicator.query.filter_by(code=code).first()
    return DataPoint.query.filter_by(indicator_id=indicator.id, division=division).count() if indicator else 0


def test_two_indicators_from_one_dataset_cost_one_request(app):
    client = StubClient(gdp_envelope())
    cache: dict = {}

    first = refresh_indicator("gdp_real_level", client, now=NOW, fetch_cache=cache)
    second = refresh_indicator("gdp_growth_yoy", client, now=NOW, fetch_cache=cache)

    assert first.ok and second.ok
    assert client.requested == ["gdp_qtr_real"]  # one provider request for both indicators
    assert stored("gdp_real_level", "abs") == 2
    assert stored("gdp_growth_yoy", "growth_yoy") == 2
    # Each indicator's rows stay separate.
    assert stored("gdp_real_level", "growth_yoy") == 0
    assert stored("gdp_growth_yoy", "abs") == 0


def test_quarterly_snapshot_reports_quarter_periods(app):
    refresh_indicator("gdp_real_level", StubClient(gdp_envelope()), now=NOW)
    snapshot = get_snapshot("gdp_real_level", now=NOW)
    assert snapshot.latest_period.isoformat() == "2026-04-01"
    assert snapshot.latest_value == Decimal("445896.454")
    assert snapshot.status == SNAPSHOT_FRESH
    assert snapshot.frequency == "QUARTERLY"


def test_snapshot_is_stale_once_the_provider_update_is_due(app):
    # Our own window is 24 hours, but the provider's next update passed earlier today.
    refresh_indicator("gdp_real_level", StubClient(gdp_envelope(next_update="2026-11-05 08:00")), now=NOW - timedelta(hours=2))
    snapshot = get_snapshot("gdp_real_level", now=NOW)
    assert snapshot.status == SNAPSHOT_STALE
    assert "next update was due on 2026-11-05" in snapshot.status_message


def test_snapshot_is_fresh_before_the_provider_update_is_due(app):
    refresh_indicator("gdp_real_level", StubClient(gdp_envelope(next_update="2026-11-18 12:00")), now=NOW)
    assert get_snapshot("gdp_real_level", now=NOW + timedelta(hours=1)).status == SNAPSHOT_FRESH


def test_unemployment_refresh_stores_rate_values(app):
    body = envelope(
        [
            {"date": "2026-08-01", "u_rate": 3.5},
            {"date": "2026-07-01", "u_rate": 3.4},
        ]
    )
    body["meta"]["update_frequency"] = "MONTHLY"
    outcome = refresh_indicator("unemployment_rate", StubClient(body), now=NOW)
    assert outcome.ok
    snapshot = get_snapshot("unemployment_rate", now=NOW)
    assert snapshot.latest_value == Decimal("3.5")
    assert snapshot.unit == "per cent of the labour force"
