"""Alerts page: sign-in, validation messages, ownership, and the notification badge."""

from datetime import datetime

from app.extensions import db
from app.models import AlertRule, Notification
from app.services.alert_service import create_rule, evaluate_all
from app.services.data_service import refresh_indicator
from tests.helpers import StubClient, cpi_row, envelope
from tests.helpers_auth import PASSWORD, create_user, sign_in

NOW = datetime(2026, 11, 5, 9, 0)


def seed_cpi(app):
    rows = [cpi_row("2026-09-01", 112.0)] + [cpi_row(f"2025-{m:02d}-01", 100.0) for m in range(9, 13)]
    rows += [cpi_row(f"2026-{m:02d}-01", 105.0) for m in range(1, 9)]
    outcome = refresh_indicator("cpi_headline", StubClient(envelope(rows)), now=NOW)
    assert outcome.ok, outcome.message


def form(**overrides):
    data = {"indicator": "cpi_headline", "alert_type": "threshold", "threshold": "3", "operator": "above"}
    data.update(overrides)
    return data


def test_alerts_page_requires_sign_in(client):
    response = client.get("/alerts")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_creating_an_alert_from_the_form(app, client):
    seed_cpi(app)
    user_id = create_user()
    sign_in(client)
    response = client.post("/alerts", data=form())
    assert response.status_code == 302
    rule = AlertRule.query.filter_by(user_id=user_id).one()
    assert str(rule.threshold_value) == "3.00"


def test_invalid_form_shows_a_message_next_to_the_field(app, client):
    seed_cpi(app)
    create_user()
    sign_in(client)
    response = client.post("/alerts", data=form(threshold="lots"))
    assert response.status_code == 400
    assert b"Enter a number, for example 3 or 2.5." in response.data
    assert b'href="#threshold"' in response.data


def test_toggle_and_delete_own_alert(app, client):
    seed_cpi(app)
    user_id = create_user()
    sign_in(client)
    client.post("/alerts", data=form())
    rule = AlertRule.query.filter_by(user_id=user_id).one()

    client.post(f"/alerts/{rule.id}/toggle")
    assert db.session.get(AlertRule, rule.id).is_active is False
    client.post(f"/alerts/{rule.id}/toggle")
    assert db.session.get(AlertRule, rule.id).is_active is True

    client.post(f"/alerts/{rule.id}/delete")
    assert db.session.get(AlertRule, rule.id) is None


def test_another_users_alert_returns_404(app, client):
    seed_cpi(app)
    owner_id = create_user("owner@example.com")
    create_rule(owner_id, "cpi_headline", "threshold", "3", "above")
    rule = AlertRule.query.filter_by(user_id=owner_id).one()

    create_user("intruder@example.com")
    sign_in(client, email="intruder@example.com")
    assert client.post(f"/alerts/{rule.id}/toggle").status_code == 404
    assert client.post(f"/alerts/{rule.id}/delete").status_code == 404
    assert db.session.get(AlertRule, rule.id) is not None


def test_another_users_notification_cannot_be_marked_read(app, client):
    seed_cpi(app)
    owner_id = create_user("owner@example.com")
    create_rule(owner_id, "cpi_headline", "threshold", "3", "above")
    evaluate_all(now=NOW)
    note = Notification.query.filter_by(user_id=owner_id).one()

    create_user("intruder@example.com")
    sign_in(client, email="intruder@example.com")
    assert client.post(f"/alerts/notifications/{note.id}/read").status_code == 404
    assert db.session.get(Notification, note.id).read_at is None


def test_notifications_list_and_badge(app, client):
    seed_cpi(app)
    user_id = create_user()
    create_rule(user_id, "cpi_headline", "threshold", "3", "above")
    evaluate_all(now=NOW)
    sign_in(client)

    html = client.get("/alerts").get_data(as_text=True)
    assert "Inflation alert: Consumer Price Index (headline)" in html
    assert "1 unread" in html
    assert 'class="badge"' in html

    note = Notification.query.filter_by(user_id=user_id).one()
    client.post(f"/alerts/notifications/{note.id}/read")
    html = client.get("/alerts").get_data(as_text=True)
    assert 'class="badge"' not in html


def test_anonymous_visitors_see_no_badge(client):
    html = client.get("/").get_data(as_text=True)
    assert 'class="badge"' not in html
    assert f'href="/alerts"' not in html


def test_evaluate_alerts_command_is_repeatable(app):
    seed_cpi(app)
    user_id = create_user()
    create_rule(user_id, "cpi_headline", "threshold", "3", "above")
    runner = app.test_cli_runner()
    first = runner.invoke(args=["evaluate-alerts"])
    second = runner.invoke(args=["evaluate-alerts"])
    assert first.exit_code == 0 and "Created 1 notification" in first.output
    assert second.exit_code == 0 and "Created 0 notification" in second.output
    assert Notification.query.filter_by(user_id=user_id).count() == 1
