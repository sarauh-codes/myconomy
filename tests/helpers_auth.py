"""Helpers for account and expense tests."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from app.extensions import db
from app.models import Expense, User

PASSWORD = "correct-horse-battery"


def create_user(email: str = "alice@example.com", password: str = PASSWORD, name: str | None = None) -> int:
    user = User(email=email, display_name=name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user.id


def add_expense(user_id: int, amount: str, category: str, month: date, note: str | None = None) -> int:
    expense = Expense(
        user_id=user_id,
        amount=Decimal(amount),
        category=category,
        expense_month=month,
        note=note,
    )
    db.session.add(expense)
    db.session.commit()
    return expense.id


def sign_in(client, email: str = "alice@example.com", password: str = PASSWORD):
    return client.post("/login", data={"email": email, "password": password})


def csrf_token_from(html: str) -> str:
    match = re.search(r'name="csrf_token" (?:type="hidden" )?value="([^"]+)"', html) or re.search(
        r'value="([^"]+)" name="csrf_token"', html
    )
    assert match, "no CSRF token in page"
    return match.group(1)
