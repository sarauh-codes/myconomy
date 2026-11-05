"""Unit tests for expense and account input rules. No database."""

from datetime import date
from decimal import Decimal

import pytest

from app.forms import check_email, parse_expense_amount, parse_month


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("0", Decimal("0")),
        ("12", Decimal("12")),
        ("12.5", Decimal("12.5")),
        ("12.50", Decimal("12.50")),
        ("1,250.75", Decimal("1250.75")),
    ],
)
def test_valid_expense_amounts(raw, expected):
    assert parse_expense_amount(raw) == expected


@pytest.mark.parametrize("raw", ["", "-1", "-0.01", "abc", "1e3", "1.234", "NaN", "10000001"])
def test_invalid_expense_amounts(raw):
    with pytest.raises(ValueError):
        parse_expense_amount(raw)


def test_month_is_first_day_of_month():
    assert parse_month("2026-03") == date(2026, 3, 1)


@pytest.mark.parametrize("raw", ["", "2026-3", "2026-00", "2026-13", "03-2026", "2026/03", "1989-12"])
def test_invalid_months(raw):
    with pytest.raises(ValueError):
        parse_month(raw)


def test_future_month_is_rejected_relative_to_today():
    today = date.today()
    next_year = f"{today.year + 1}-01"
    with pytest.raises(ValueError, match="current month or an earlier one"):
        parse_month(next_year)


@pytest.mark.parametrize("email", ["a@b.co", "first.last@example.org"])
def test_valid_emails(email):
    assert check_email(email) is None


@pytest.mark.parametrize("email", ["", "no-at-sign", "a@b", "two@@signs.com", "space in@example.com"])
def test_invalid_emails(email):
    assert check_email(email) is not None
