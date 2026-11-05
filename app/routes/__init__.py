"""Blueprint registration. Add each new feature blueprint in one place."""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    from .calculator import calculator_bp
    from .dashboard import dashboard_bp
    from .data_status import data_status_bp
    from .main import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(data_status_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(calculator_bp)
