"""Personal monthly spending records. Each record belongs to exactly one user."""

from decimal import Decimal

from ..extensions import db
from .indicator import utcnow


class Expense(db.Model):
    __tablename__ = "expenses"
    __table_args__ = (
        db.Index("ix_expenses_user_month", "user_id", "expense_month"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    category = db.Column(db.String(40), nullable=False)
    # Stored as the first day of the month, e.g. 2026-09-01 for September 2026.
    expense_month = db.Column(db.Date, nullable=False)
    note = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    user = db.relationship("User", back_populates="expenses")
