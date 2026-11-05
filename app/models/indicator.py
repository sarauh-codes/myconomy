"""Registry rows for indicators. The verified mapping itself lives in services/dataset_registry.py."""

from datetime import datetime, timezone

from ..extensions import db


def utcnow() -> datetime:
    """Naive UTC timestamp. All stored times are UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Indicator(db.Model):
    __tablename__ = "indicators"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    provider = db.Column(db.String(64), nullable=False)
    dataset_id = db.Column(db.String(128), nullable=False)
    unit = db.Column(db.String(200), nullable=False)
    frequency = db.Column(db.String(32), nullable=False)
    source_url = db.Column(db.String(500), nullable=False)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    data_points = db.relationship("DataPoint", back_populates="indicator", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Indicator {self.code}>"
