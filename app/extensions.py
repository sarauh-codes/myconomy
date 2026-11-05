"""Flask extensions, created here and bound to the app in the factory.

Creating them at module level (without an app) avoids circular imports:
models and routes can import `db` without importing the application.
"""

from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
