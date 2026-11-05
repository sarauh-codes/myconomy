"""Release hardening: sign-in lockout, security headers, and health reporting."""

from datetime import datetime, timedelta

from app.extensions import db
from app.models import User
from app.models.indicator import utcnow
from tests.helpers_auth import PASSWORD, create_user, sign_in


# Lockout


def test_account_locks_after_repeated_failures(app, client):
    user_id = create_user()
    for _ in range(5):
        sign_in(client, password="wrong-password-value")
    user = db.session.get(User, user_id)
    assert user.locked_until is not None
    assert user.locked_until > utcnow()


def test_locked_account_refuses_the_correct_password(app, client):
    user_id = create_user()
    db.session.get(User, user_id).locked_until = utcnow() + timedelta(minutes=10)
    db.session.commit()
    response = sign_in(client, password=PASSWORD)
    assert response.status_code == 400
    assert response.headers.get("Location") is None
    assert b"Email or password is not correct." in response.data


def test_lock_message_is_the_same_as_any_failure(app, client):
    create_user()
    wrong = sign_in(client, password="wrong-password-value").get_data(as_text=True)
    unknown = sign_in(client, email="nobody@example.com").get_data(as_text=True)
    assert "After several failed attempts" in wrong
    assert "After several failed attempts" in unknown


def test_lock_expires_and_correct_password_works_again(app, client):
    user_id = create_user()
    user = db.session.get(User, user_id)
    user.locked_until = utcnow() - timedelta(minutes=1)
    user.failed_login_count = 4
    db.session.commit()
    response = sign_in(client, password=PASSWORD)
    assert response.status_code == 302
    user = db.session.get(User, user_id)
    assert user.failed_login_count == 0
    assert user.locked_until is None


def test_successful_sign_in_resets_the_failure_count(app, client):
    user_id = create_user()
    sign_in(client, password="wrong-password-value")
    sign_in(client, password="wrong-password-value")
    assert db.session.get(User, user_id).failed_login_count == 2
    sign_in(client, password=PASSWORD)
    assert db.session.get(User, user_id).failed_login_count == 0


def test_unknown_email_does_not_change_any_account(app, client):
    user_id = create_user()
    for _ in range(6):
        sign_in(client, email="nobody@example.com", password="wrong-password-value")
    assert db.session.get(User, user_id).failed_login_count == 0


# Security headers


def test_content_security_policy_allows_only_the_known_sources(client):
    csp = client.get("/").headers["Content-Security-Policy"]
    assert "script-src 'self' https://cdnjs.cloudflare.com" in csp
    assert "style-src 'self' https://fonts.googleapis.com" in csp
    assert "frame-ancestors 'none'" in csp
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp


def test_permissions_policy_disables_sensitive_features(client):
    policy = client.get("/").headers["Permissions-Policy"]
    assert "camera=()" in policy and "microphone=()" in policy and "geolocation=()" in policy


def test_hsts_is_sent_only_when_cookies_are_secure(app, client):
    assert "Strict-Transport-Security" not in client.get("/").headers
    app.config["SESSION_COOKIE_SECURE"] = True
    assert "max-age=31536000" in client.get("/").headers["Strict-Transport-Security"]
    app.config["SESSION_COOKIE_SECURE"] = False


def test_every_page_carries_the_csp_header(client):
    for path in ["/", "/dashboard", "/calculator", "/learn", "/chat", "/login", "/nope"]:
        response = client.get(path)
        assert "Content-Security-Policy" in response.headers, path


# Health


def test_health_check_stays_ok_when_data_is_unavailable(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert set(response.get_json()["data"].values()) == {"unavailable"}
