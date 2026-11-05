"""Refresh status and provider metadata for each cached indicator.

The status records the outcome of the most recent refresh. The observations
themselves live in data_points, so a failed refresh never removes them.
"""

from ..extensions import db
from .indicator import utcnow


class CacheEntry(db.Model):
    __tablename__ = "cache_entries"

    id = db.Column(db.Integer, primary_key=True)
    cache_key = db.Column(db.String(128), unique=True, nullable=False)
    # success: last refresh worked. stale: last refresh failed, previous data kept.
    # error: last refresh failed and no earlier data exists.
    status = db.Column(db.String(16), nullable=False)
    fetched_at = db.Column(db.DateTime, nullable=True)  # when the last successful refresh finished
    expires_at = db.Column(db.DateTime, nullable=True)
    reference_period = db.Column(db.String(32), nullable=True)  # provider's data_as_of, e.g. "2026-09"
    source_last_updated = db.Column(db.DateTime, nullable=True)
    source_next_update = db.Column(db.DateTime, nullable=True)
    update_frequency = db.Column(db.String(32), nullable=True)
    last_attempt_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    last_error = db.Column(db.String(500), nullable=True)  # sanitised, never contains secrets
