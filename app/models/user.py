"""User accounts. Passwords are stored only as salted hashes, never in plain text."""

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from .indicator import utcnow


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # The ORM deletes these records itself. Relying on the database cascade alone
    # would leave them behind on SQLite, which does not enforce foreign keys by default.
    expenses = db.relationship(
        "Expense",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        # Never include the email or hash in logs or debug output.
        return f"<User {self.id}>"
