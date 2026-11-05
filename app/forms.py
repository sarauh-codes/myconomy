"""Forms with server-side validation. Each form includes a CSRF token."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, ValidationError

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128
CATEGORIES = [
    "Food and drink",
    "Transport",
    "Housing",
    "Utilities",
    "Health",
    "Education",
    "Clothing",
    "Entertainment",
    "Other",
]
MAX_EXPENSE_AMOUNT = Decimal("10000000")  # RM 10 million per record
EARLIEST_EXPENSE_MONTH = date(1990, 1, 1)


def normalise_email(raw: str) -> str:
    return (raw or "").strip().lower()


def check_email(value: str) -> str | None:
    email = normalise_email(value)
    if not email or len(email) > 254 or not EMAIL_PATTERN.match(email):
        return "Enter a valid email address."
    return None


def parse_expense_amount(raw: str) -> Decimal:
    """Return a valid non-negative amount with at most two decimal places. Raises ValueError."""
    text = (raw or "").strip().replace(",", "")
    if not text or text.startswith("-"):
        raise ValueError("The amount must be zero or positive.")
    if not re.match(r"^\d+(\.\d{1,2})?$", text):
        raise ValueError("Enter an amount with up to two decimal places, for example 12.50.")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:  # pragma: no cover - the pattern already guards this
        raise ValueError("Enter a valid amount.") from exc
    if amount > MAX_EXPENSE_AMOUNT:
        raise ValueError("The amount is too large for one record.")
    return amount


def parse_month(raw: str) -> date:
    """Return the first day of the month for a YYYY-MM value. Raises ValueError."""
    match = re.match(r"^(\d{4})-(0[1-9]|1[0-2])$", (raw or "").strip())
    if not match:
        raise ValueError("Use the format YYYY-MM for the month.")
    month = date(int(match.group(1)), int(match.group(2)), 1)
    if month < EARLIEST_EXPENSE_MONTH:
        raise ValueError("Choose a month from 1990 onwards.")
    today = date.today()
    if month > date(today.year, today.month, 1):
        raise ValueError("Choose the current month or an earlier one.")
    return month


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Length(max=254)])
    display_name = StringField("Display name (optional)", validators=[Length(max=100)])
    password = PasswordField("Password", validators=[DataRequired()])
    confirm = PasswordField("Confirm password", validators=[DataRequired()])
    submit = SubmitField("Create account")

    def validate_email(self, field):
        problem = check_email(field.data)
        if problem:
            raise ValidationError(problem)

    def validate_password(self, field):
        if len(field.data or "") < MIN_PASSWORD_LENGTH:
            raise ValidationError(f"Use at least {MIN_PASSWORD_LENGTH} characters.")
        if len(field.data) > MAX_PASSWORD_LENGTH:
            raise ValidationError(f"Use no more than {MAX_PASSWORD_LENGTH} characters.")

    def validate_confirm(self, field):
        if field.data != self.password.data:
            raise ValidationError("The passwords do not match.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Length(max=254)])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=MAX_PASSWORD_LENGTH)])
    submit = SubmitField("Sign in")


class DeleteAccountForm(FlaskForm):
    password = PasswordField("Confirm your password", validators=[DataRequired(), Length(max=MAX_PASSWORD_LENGTH)])
    submit = SubmitField("Delete my account")


class ExpenseForm(FlaskForm):
    amount = StringField("Amount (RM)", validators=[DataRequired(), Length(max=20)])
    category = SelectField("Category", choices=list(CATEGORIES), validators=[DataRequired()])
    # No length rule here: parse_month gives a clearer message for malformed months.
    month = StringField("Month", validators=[DataRequired()])
    note = TextAreaField("Note (optional)", validators=[Length(max=200)])
    submit = SubmitField("Save")
