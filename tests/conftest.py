"""Shared test fixtures.

Tests always use the TestingConfig, which points at an in-memory SQLite
database, so no real or development data is read or changed.
"""

import pytest

from app import create_app
from app.extensions import db


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
