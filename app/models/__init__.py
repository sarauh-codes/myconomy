"""ORM models. Importing this package registers every table with SQLAlchemy metadata,
which Flask-Migrate needs to generate migrations."""

from .alert import AlertRule, Notification
from .cache_entry import CacheEntry
from .data_point import DataPoint
from .expense import Expense
from .indicator import Indicator
from .user import User

__all__ = ["AlertRule", "CacheEntry", "DataPoint", "Expense", "Indicator", "Notification", "User"]
