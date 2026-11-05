"""Route tests for the public home page, health check, and error pages."""

from app.extensions import db


def test_home_page_is_public_and_shows_title(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Understand Malaysia" in response.data


def test_home_page_has_language_and_skip_link(client):
    html = client.get("/").get_data(as_text=True)
    assert 'lang="en"' in html
    assert 'href="#main"' in html


def test_home_page_offers_both_themes_and_toggle_is_hidden_until_js(client):
    html = client.get("/").get_data(as_text=True)
    assert 'data-theme-toggle hidden' in html
    assert 'rel="stylesheet" href="https://fonts.googleapis.com/' in html


def test_home_page_shows_no_hardcoded_economic_figures(client):
    # Figures must come from OpenDOSM (Milestone 2), never typed into templates.
    html = client.get("/").get_data(as_text=True)
    assert "137.6" not in html
    assert "CPI" not in html.split('<section class="facts"')[0]


def test_health_check_reports_ok(client):
    response = client.get("/health")
    body = response.get_json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    # Data status is reported but does not make the app unhealthy.
    assert set(body["data"]) == {"cpi_headline", "unemployment_rate", "gdp_real_level", "gdp_growth_yoy"}


def test_health_check_returns_503_when_database_fails(client, monkeypatch):
    def broken_execute(*args, **kwargs):
        raise RuntimeError("simulated database failure")

    monkeypatch.setattr(db.session, "execute", broken_execute)
    response = client.get("/health")
    assert response.status_code == 503
    body = response.get_json()
    assert body == {"status": "error", "database": "unavailable"}
    # Internal error details must not leak to the caller.
    assert "simulated" not in response.get_data(as_text=True)


def test_unknown_page_shows_friendly_404(client):
    response = client.get("/no-such-page")
    assert response.status_code == 404
    assert b"Page not found" in response.data
    assert b"Traceback" not in response.data


def test_security_headers_are_set(client):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_server_error_shows_generic_page_without_details(app, client):
    @app.get("/boom")
    def boom():
        raise ValueError("secret internal detail")

    app.config["PROPAGATE_EXCEPTIONS"] = False
    response = client.get("/boom")
    assert response.status_code == 500
    assert b"Something went wrong" in response.data
    assert b"secret internal detail" not in response.data
