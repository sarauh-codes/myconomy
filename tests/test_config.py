"""Configuration and application-factory behaviour."""

import pytest

from app import create_app


def test_unknown_configuration_name_is_rejected():
    with pytest.raises(ValueError):
        create_app("staging")


def test_production_requires_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app("production")


def test_testing_config_uses_in_memory_database():
    app = create_app("testing")
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
    assert app.config["TESTING"] is True


def test_development_generates_secret_when_none_is_set(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    app = create_app("development")
    assert app.config["SECRET_KEY"]
    assert app.config["SECRET_KEY"] != "test-only-secret-key"
