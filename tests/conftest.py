"""Shared test fixtures.

Tests always use the TestingConfig, which points at an in-memory SQLite
database, so no real or development data is read or changed.
"""

from datetime import datetime

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture(autouse=True)
def frozen_data_clock(monkeypatch):
    """Freeze the clock used to judge data freshness, so tests seeded at a fixed time stay deterministic."""
    from app.services import data_service

    monkeypatch.setattr(data_service, "utcnow", lambda: datetime(2026, 11, 5, 9, 0))


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
