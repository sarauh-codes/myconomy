"""Flask extensions, created here and bound to the app in the factory.

Creating them at module level (without an app) avoids circular imports:
models and routes can import `db` without importing the application.
"""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
