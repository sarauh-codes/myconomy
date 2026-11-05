"""Blueprint registration. Add each new feature blueprint in one place."""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    from .auth import auth_bp
    from .expenses import expenses_bp
    from .calculator import calculator_bp
    from .dashboard import dashboard_bp
    from .explore import explore_bp
    from .data_status import data_status_bp
    from .learn import learn_bp
    from .main import main_bp
    from .widget import widget_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(data_status_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(calculator_bp)
    app.register_blueprint(learn_bp)
    app.register_blueprint(explore_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(widget_bp)
