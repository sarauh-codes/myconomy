"""Inflation alerts: thresholds, new-data events, idempotence, failures, and inactive rules."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.extensions import db
from app.models import AlertRule, Notification
from app.services.alert_service import AlertError, create_rule, evaluate_all, mark_read, unread_count
from app.services.data_service import refresh_indicator
from app.services.opendosm_client import UpstreamUnavailable
from tests.helpers import StubClient, cpi_row, envelope
from tests.helpers_auth import create_user

NOW = datetime(2026, 11, 5, 9, 0)


def cpi_series(end_value: float = 112.0) -> list[dict]:
    """Thirteen months from Sep 2025 (100.0) to Sep 2026 (end_value). Year-on-year change = end/100 - 1."""
    rows = []
    for i in range(13):
        year = 2025 + (8 + i) // 12
        month = (8 + i) % 12 + 1
        value = 100.0 + (end_value - 100.0) * i / 12
        rows.append(cpi_row(date(year, month, 1).isoformat(), round(value, 1)))
    return list(reversed(rows))


def seed(rows, *, now=NOW):
    outcome = refresh_indicator("cpi_headline", StubClient(envelope(rows)), now=now)
    assert outcome.ok, outcome.message


def notes_for(user_id: int) -> list[Notification]:
    return Notification.query.filter_by(user_id=user_id).order_by(Notification.id).all()


# ALERT-01


def test_threshold_rule_is_saved_with_its_settings(app):
    user_id = create_user()
    seed(cpi_series())
    rule = create_rule(user_id, "cpi_headline", "threshold", "3.5", "above")
    stored = db.session.get(AlertRule, rule.id)
    assert stored.alert_type == "threshold"
    assert stored.threshold_value == Decimal("3.50")
    assert stored.comparison_operator == "above"
    assert stored.is_active is True
    assert stored.delivery_method == "in_app"


# ALERT-02


def test_threshold_crossing_creates_one_notification_with_period_and_source(app):
    user_id = create_user()
    seed(cpi_series(112.0))  # 12% year-on-year
    create_rule(user_id, "cpi_headline", "threshold", "10", "above")

    report = evaluate_all(now=NOW)

    assert report.created == 1
    [note] = notes_for(user_id)
    assert note.reference_period == date(2026, 9, 1)
    assert note.source_url.startswith("https://developer.data.gov.my/")
    assert "+12.0%" in note.message
    assert "2025-09" in note.message
    assert "Source: OpenDOSM" in note.message


def test_threshold_not_crossed_creates_nothing(app):
    user_id = create_user()
    seed(cpi_series(112.0))
    create_rule(user_id, "cpi_headline", "threshold", "15", "above")
    assert evaluate_all(now=NOW).created == 0
    assert notes_for(user_id) == []


def test_below_threshold_direction(app):
    user_id = create_user()
    seed(cpi_series(101.0))  # 1% year-on-year
    create_rule(user_id, "cpi_headline", "threshold", "2", "below")
    assert evaluate_all(now=NOW).created == 1


# ALERT-03


def test_evaluating_the_same_event_twice_creates_no_duplicate(app):
    user_id = create_user()
    seed(cpi_series(112.0))
    create_rule(user_id, "cpi_headline", "threshold", "10", "above")

    first = evaluate_all(now=NOW)
    second = evaluate_all(now=NOW + timedelta(hours=1))

    assert first.created == 1
    assert second.created == 0
    assert len(notes_for(user_id)) == 1


def test_a_second_refresh_with_the_same_data_creates_no_duplicate(app):
    user_id = create_user()
    seed(cpi_series(112.0))
    create_rule(user_id, "cpi_headline", "threshold", "10", "above")
    evaluate_all(now=NOW)
    seed(cpi_series(112.0), now=NOW + timedelta(hours=13))
    evaluate_all(now=NOW + timedelta(hours=13))
    assert len(notes_for(user_id)) == 1


# ALERT-04


def test_new_period_triggers_one_new_data_alert(app):
    user_id = create_user()
    seed(cpi_series(112.0))
    create_rule(user_id, "cpi_headline", "new_data", None, None)

    # The rule's baseline is the latest stored period, so nothing alerts yet.
    assert evaluate_all(now=NOW).created == 0

    newer = [cpi_row("2026-10-01", 112.5)] + cpi_series(112.0)
    seed(newer, now=NOW + timedelta(days=30))
    assert evaluate_all(now=NOW + timedelta(days=30)).created == 1
    assert evaluate_all(now=NOW + timedelta(days=31)).created == 0

    [note] = notes_for(user_id)
    assert note.reference_period == date(2026, 10, 1)
    assert "2026-10" in note.message


def test_new_data_alert_does_not_fire_for_existing_periods_on_creation(app):
    user_id = create_user()
    seed(cpi_series(112.0))
    create_rule(user_id, "cpi_headline", "new_data", None, None)
    evaluate_all(now=NOW)
    evaluate_all(now=NOW + timedelta(days=1))
    assert notes_for(user_id) == []


# ALERT-05


def test_failed_refresh_creates_no_false_new_data_alert(app):
    user_id = create_user()
    seed(cpi_series(112.0))
    create_rule(user_id, "cpi_headline", "new_data", None, None)
    evaluate_all(now=NOW)

    refresh_indicator("cpi_headline", StubClient(UpstreamUnavailable("down")), now=NOW + timedelta(days=1))
    report = evaluate_all(now=NOW + timedelta(days=1))

    assert report.created == 0
    assert notes_for(user_id) == []


def test_empty_refresh_creates_no_alert(app):
    user_id = create_user()
    seed(cpi_series(112.0))
    create_rule(user_id, "cpi_headline", "threshold", "10", "above")
    refresh_indicator("cpi_headline", StubClient(envelope([])), now=NOW + timedelta(days=1))
    assert evaluate_all(now=NOW + timedelta(days=1)).created == 0


# ALERT-06


def test_inactive_rule_creates_no_notification(app):
    user_id = create_user()
    seed(cpi_series(112.0))
    rule = create_rule(user_id, "cpi_headline", "threshold", "10", "above")
    rule.is_active = False
    db.session.commit()
    assert evaluate_all(now=NOW).created == 0


def test_inactive_account_is_skipped(app):
    from app.models import User

    user_id = create_user()
    seed(cpi_series(112.0))
    create_rule(user_id, "cpi_headline", "threshold", "10", "above")
    db.session.get(User, user_id).is_active = False
    db.session.commit()
    assert evaluate_all(now=NOW).created == 0


def test_one_bad_rule_does_not_stop_the_others(app, monkeypatch):
    seed(cpi_series(112.0))
    bad_user = create_user("bad@example.com")
    good_user = create_user("good@example.com")
    create_rule(bad_user, "cpi_headline", "threshold", "10", "above")
    create_rule(good_user, "cpi_headline", "threshold", "10", "above")

    from app.services import alert_service

    original = alert_service.evaluate_rule

    def flaky(rule, *, now):
        if rule.user_id == bad_user:
            raise RuntimeError("simulated failure")
        return original(rule, now=now)

    monkeypatch.setattr(alert_service, "evaluate_rule", flaky)
    report = evaluate_all(now=NOW)
    assert report.created == 1
    assert len(report.skipped) == 1
    assert len(notes_for(good_user)) == 1


# Validation


@pytest.mark.parametrize(
    "indicator, alert_type, threshold, operator, field",
    [
        ("nope", "threshold", "3", "above", "indicator"),
        ("cpi_headline", "weekly", "3", "above", "alert_type"),
        ("cpi_headline", "threshold", "", "above", "threshold"),
        ("cpi_headline", "threshold", "abc", "above", "threshold"),
        ("cpi_headline", "threshold", "500", "above", "threshold"),
        ("cpi_headline", "threshold", "3", "sideways", "operator"),
        ("unemployment_rate", "threshold", "3", "above", "indicator"),
    ],
)
def test_invalid_rules_are_rejected_with_a_field_message(app, indicator, alert_type, threshold, operator, field):
    user_id = create_user()
    seed(cpi_series(112.0))
    with pytest.raises(AlertError) as raised:
        create_rule(user_id, indicator, alert_type, threshold, operator)
    assert field in raised.value.errors
    assert AlertRule.query.count() == 0


def test_new_data_rule_on_a_rate_is_allowed(app):
    user_id = create_user()
    body = envelope([{"date": "2026-08-01", "u_rate": 2.9}])
    body["meta"]["update_frequency"] = "MONTHLY"
    refresh_indicator("unemployment_rate", StubClient(body), now=NOW)
    rule = create_rule(user_id, "unemployment_rate", "new_data", None, None)
    assert rule.threshold_value is None


def test_rule_limit_is_enforced(app, monkeypatch):
    from app.services import alert_service

    monkeypatch.setattr(alert_service, "MAX_RULES_PER_USER", 2)
    user_id = create_user()
    seed(cpi_series(112.0))
    create_rule(user_id, "cpi_headline", "new_data", None, None)
    create_rule(user_id, "cpi_headline", "threshold", "3", "above")
    with pytest.raises(AlertError, match="up to 2"):
        create_rule(user_id, "cpi_headline", "threshold", "4", "above")


def test_no_stored_data_means_no_rule_yet(app):
    user_id = create_user()
    with pytest.raises(AlertError, match="Run the data refresh first"):
        create_rule(user_id, "cpi_headline", "new_data", None, None)


# Read state


def test_marking_read_updates_the_unread_count(app):
    user_id = create_user()
    seed(cpi_series(112.0))
    create_rule(user_id, "cpi_headline", "threshold", "10", "above")
    evaluate_all(now=NOW)
    assert unread_count(user_id) == 1
    [note] = notes_for(user_id)
    assert mark_read(user_id, note.id) is True
    assert unread_count(user_id) == 0


def test_another_user_cannot_mark_a_notification_read(app):
    owner = create_user("owner@example.com")
    other = create_user("other@example.com")
    seed(cpi_series(112.0))
    create_rule(owner, "cpi_headline", "threshold", "10", "above")
    evaluate_all(now=NOW)
    [note] = notes_for(owner)
    assert mark_read(other, note.id) is False
    assert unread_count(owner) == 1
