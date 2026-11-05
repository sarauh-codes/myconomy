"""Application factory for Myconomy.

`create_app()` builds a configured Flask instance. Tests and the command line
call it with different configurations, so no global app object is needed.
"""

import logging
import os

from flask import Flask

from .config import config_by_name
from .extensions import csrf, db, login_manager, migrate


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application."""
    name = config_name or os.environ.get("FLASK_CONFIG", "development")
    if name not in config_by_name:
        raise ValueError(f"Unknown configuration '{name}'. Choose from: {', '.join(config_by_name)}.")

    app = Flask(__name__)
    app.config.from_object(config_by_name[name])

    if not app.config["SECRET_KEY"]:
        # Fail at startup rather than run with weak or missing session security.
        raise RuntimeError("SECRET_KEY must be set in the environment for this configuration.")

    _configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    _configure_login(app)

    # Import models so their tables are registered for migrations.
    from . import models  # noqa: F401

    from .cli import register_commands
    from .errors import register_error_handlers
    from .routes import register_blueprints

    from .services.dataset_registry import format_period

    app.add_template_filter(format_period, "period")

    register_blueprints(app)
    register_error_handlers(app)
    register_commands(app)
    _register_security_headers(app)

    return app


def _configure_login(app: Flask) -> None:
    """Sign-in is optional for most of the site. Only personal pages require it."""
    from .models import User

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to see that page."
    login_manager.login_message_category = "notice"

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            user = db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None
        return user if user is not None and user.is_active else None


def _configure_logging(app: Flask) -> None:
    """Log to the console at the configured level. Never log secrets or personal data."""
    logging.basicConfig(
        level=app.config["LOG_LEVEL"],
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _register_security_headers(app: Flask) -> None:
    """Send baseline headers that limit common browser-side attacks."""

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response
