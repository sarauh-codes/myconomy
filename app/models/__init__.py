"""ORM models. Importing this package registers every table with SQLAlchemy metadata,
which Flask-Migrate needs to generate migrations."""

from .cache_entry import CacheEntry
from .data_point import DataPoint
from .indicator import Indicator

__all__ = ["CacheEntry", "DataPoint", "Indicator"]
