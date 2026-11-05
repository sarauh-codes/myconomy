"""Blueprint registration. Add each new feature blueprint in one place."""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    from .main import main_bp

    app.register_blueprint(main_bp)
