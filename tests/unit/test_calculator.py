"""Unit tests for the purchasing power formula and input validation. No database."""

from datetime import date
from decimal import Decimal

import pytest

from app.services.calculator_service import (
    CalculationError,
    equivalent_amount,
    parse_amount,
    parse_period,
    validate_input,
)


def test_formula_matches_independent_calculation():
    # 100 × (137.6 ÷ 126.5) = 108.77 (rounded to the cent)
    ratio, value = equivalent_amount(Decimal("100"), Decimal("126.5"), Decimal("137.6"))
    assert ratio == Decimal("1.0877")
    assert value == Decimal("108.77")


def test_direction_is_correct_when_cpi_falls():
    # Target CPI lower than starting CPI: the equivalent amount is smaller.
    _, value = equivalent_amount(Decimal("100"), Decimal("137.6"), Decimal("126.5"))
    assert value == Decimal("91.93")


def test_same_month_returns_the_input_amount():
    _, value = equivalent_amount(Decimal("250.00"), Decimal("130.0"), Decimal("130.0"))
    assert value == Decimal("250.00")


def test_zero_amount_gives_zero():
    _, value = equivalent_amount(Decimal("0"), Decimal("100"), Decimal("120"))
    assert value == Decimal("0.00")


@pytest.mark.parametrize("source, target", [(None, Decimal("1")), (Decimal("1"), None)])
def test_missing_cpi_is_rejected_not_estimated(source, target):
    with pytest.raises(CalculationError, match="missing"):
        equivalent_amount(Decimal("100"), source, target)


@pytest.mark.parametrize("source, target", [(Decimal("0"), Decimal("1")), (Decimal("1"), Decimal("-2"))])
def test_zero_or_negative_cpi_is_rejected(source, target):
    with pytest.raises(CalculationError, match="positive"):
        equivalent_amount(Decimal("100"), source, target)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("1000", Decimal("1000")),
        ("250.50", Decimal("250.50")),
        ("1,000.50", Decimal("1000.50")),
        (" 0 ", Decimal("0")),
        ("0.5", Decimal("0.5")),
    ],
)
def test_valid_amounts_are_accepted(raw, expected):
    amount, error = parse_amount(raw)
    assert error is None
    assert amount == expected


@pytest.mark.parametrize(
    "raw, message",
    [
        ("", "Enter an amount."),
        ("   ", "Enter an amount."),
        ("-5", "zero or positive"),
        ("abc", "Enter a number"),
        ("1e3", "Enter a number"),
        ("NaN", "Enter a number"),
        ("Infinity", "Enter a number"),
        ("1.234", "Enter a number"),
        ("1000000000000000", "too large"),
    ],
)
def test_invalid_amounts_are_rejected(raw, message):
    amount, error = parse_amount(raw)
    assert amount is None
    assert message in error


def test_spaces_inside_amount_are_removed():
    amount, error = parse_amount("12 345.6")
    assert error is None
    assert amount == Decimal("12345.6")


@pytest.mark.parametrize("raw", ["2020-01", "2026-12", "1999-07"])
def test_valid_periods_become_first_of_month(raw):
    period, error = parse_period(raw, "starting")
    assert error is None
    assert period.day == 1
    assert period.strftime("%Y-%m") == raw


@pytest.mark.parametrize("raw", ["", "2020-13", "2020-00", "2020/01", "01-2020", "2020-1", "Jan 2020"])
def test_invalid_periods_are_rejected(raw):
    period, error = parse_period(raw, "target")
    assert period is None
    assert error


def test_validate_input_collects_errors_per_field():
    result = validate_input("-1", "2020-99", "")
    assert set(result.errors) == {"amount", "source", "target"}
    assert result.values is None


def test_validate_input_returns_typed_values_when_valid():
    result = validate_input("100", "2020-01", "2026-09")
    assert result.errors == {}
    assert result.values.amount == Decimal("100")
    assert result.values.source_period == date(2020, 1, 1)
    assert result.values.target_period == date(2026, 9, 1)
