"""Application configuration.

Settings come from environment variables wherever a value can differ between
machines or deployments. Secrets are never written into this file.
"""

import os
import secrets


class BaseConfig:
    """Settings shared by every environment."""

    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get("SECRET_KEY")
    # Relative SQLite paths are stored in the Flask instance/ folder.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///myconomy.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")


class DevelopmentConfig(BaseConfig):
    """Local development. A random secret is generated if none is set.

    The random key means sessions are invalidated on each restart, which is
    acceptable for local work and avoids shipping a known default secret.
    """

    DEBUG = True
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)


class TestingConfig(BaseConfig):
    """Automated tests. Uses an in-memory database so real data is never touched."""

    TESTING = True
    SECRET_KEY = "test-only-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(BaseConfig):
    """Deployed use. SECRET_KEY must be supplied by the environment."""

    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
