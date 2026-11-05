"""Normalised observations. One row per indicator, period, and dimension."""

from datetime import date

from ..extensions import db
from .indicator import utcnow


class DataPoint(db.Model):
    __tablename__ = "data_points"
    __table_args__ = (
        # The uniqueness rule that makes refreshes idempotent: rerunning a refresh
        # updates existing rows instead of duplicating them.
        db.UniqueConstraint("indicator_id", "reference_period", "division", name="uq_data_point_observation"),
        db.Index("ix_data_points_indicator_period", "indicator_id", "reference_period"),
    )

    id = db.Column(db.Integer, primary_key=True)
    indicator_id = db.Column(db.Integer, db.ForeignKey("indicators.id"), nullable=False)
    reference_period = db.Column(db.Date, nullable=False)
    # Empty string when the dataset has no division dimension.
    division = db.Column(db.String(32), nullable=False, default="")
    # Null means the provider reported the value as missing for this period.
    value = db.Column(db.Numeric(18, 4), nullable=True)
    unit = db.Column(db.String(200), nullable=False)
    fetched_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    source_updated_at = db.Column(db.DateTime, nullable=True)

    indicator = db.relationship("Indicator", back_populates="data_points")
