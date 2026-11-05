"""Inflation alerts: a user's rules and the notifications they produce.

Each notification has a unique event_key. The key is built from the rule, the
alert type, and the source period (and value, for threshold alerts), so
running the evaluation again cannot create a duplicate.
"""

from datetime import date

from ..extensions import db
from .indicator import utcnow

ALERT_TYPES = ("threshold", "new_data")
OPERATORS = ("above", "below")


class AlertRule(db.Model):
    __tablename__ = "alert_rules"
    __table_args__ = (db.Index("ix_alert_rules_user_active", "user_id", "is_active"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    indicator_id = db.Column(db.Integer, db.ForeignKey("indicators.id"), nullable=False)
    alert_type = db.Column(db.String(16), nullable=False)
    # threshold rules only: the percentage change to compare against, and the direction.
    threshold_value = db.Column(db.Numeric(10, 2), nullable=True)
    comparison_operator = db.Column(db.String(8), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    delivery_method = db.Column(db.String(16), nullable=False, default="in_app")
    # new_data rules only: the latest period already seen, so only newer periods alert.
    last_seen_period = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    indicator = db.relationship("Indicator")
    notifications = db.relationship(
        "Notification",
        back_populates="alert_rule",
        cascade="all, delete-orphan",
    )


class Notification(db.Model):
    __tablename__ = "notifications"
    __table_args__ = (db.Index("ix_notifications_user_created", "user_id", "created_at"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    alert_rule_id = db.Column(db.Integer, db.ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=True)
    event_key = db.Column(db.String(200), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    reference_period = db.Column(db.Date, nullable=True)
    source_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    read_at = db.Column(db.DateTime, nullable=True)
    delivery_status = db.Column(db.String(16), nullable=False, default="delivered")

    alert_rule = db.relationship("AlertRule", back_populates="notifications")

    @property
    def is_read(self) -> bool:
        return self.read_at is not None


def period_key(period: date) -> str:
    return period.strftime("%Y-%m-%d")
