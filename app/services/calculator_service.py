"""Purchasing power calculator.

Formula (FR-02):
    equivalent_amount = input_amount × (CPI_target / CPI_source)

The result is an estimate based on the national headline CPI. It is not a
measure of any individual's costs.

Validation happens here on the server, so the page and any future API share the same rules.
Errors are returned per field. Nothing is estimated when a CPI value is
missing: the calculation stops and says which month is unavailable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from .dashboard_service import load_points
from .data_service import Snapshot, get_snapshot
from .dataset_registry import get_indicator

CPI_CODE = "cpi_headline"
# Shared by the calculator page and the learning pages, so the explanation
# can never drift from the implemented calculation.
FORMULA_TEXT = "equivalent amount = input amount × (target CPI ÷ starting CPI)"
CENT = Decimal("0.01")
MAX_AMOUNT = Decimal("1000000000000")  # RM 1 trillion; rejects absurd inputs
AMOUNT_PATTERN = re.compile(r"^\d+(\.\d{1,2})?$")
PERIOD_PATTERN = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


class CalculationError(Exception):
    """A calculation cannot be carried out with the stored data."""


@dataclass(frozen=True)
class CalculationInput:
    amount: Decimal
    source_period: date
    target_period: date


@dataclass(frozen=True)
class CalculationResult:
    inputs: CalculationInput
    source_cpi: Decimal
    target_cpi: Decimal
    ratio: Decimal  # target / source, four decimal places
    equivalent_amount: Decimal
    change_pct: Decimal  # (equivalent - amount) / amount × 100, or 0 when amount is 0
    snapshot: Snapshot
    available_from: date | None
    available_to: date | None


@dataclass
class ValidationResult:
    values: CalculationInput | None = None
    errors: dict[str, str] = field(default_factory=dict)


def parse_amount(raw: str | None) -> tuple[Decimal | None, str | None]:
    """Return (amount, error). Accepts digits with an optional decimal part and thousands commas."""
    text = (raw or "").strip().replace(",", "").replace(" ", "")
    if not text:
        return None, "Enter an amount."
    if text.startswith("-"):
        return None, "The amount must be zero or positive."
    if not AMOUNT_PATTERN.match(text):
        return None, "Enter a number with up to two decimal places, for example 1000 or 250.50."
    amount = Decimal(text)
    if amount > MAX_AMOUNT:
        return None, "The amount is too large."
    return amount, None


def parse_period(raw: str | None, label: str) -> tuple[date | None, str | None]:
    """Return (first day of month, error). Accepts YYYY-MM."""
    text = (raw or "").strip()
    if not text:
        return None, f"Choose a {label} month."
    match = PERIOD_PATTERN.match(text)
    if not match:
        return None, f"Use the format YYYY-MM for the {label} month."
    return date(int(match.group(1)), int(match.group(2)), 1), None


def validate_input(amount_raw: str | None, source_raw: str | None, target_raw: str | None) -> ValidationResult:
    result = ValidationResult()
    amount, amount_error = parse_amount(amount_raw)
    source, source_error = parse_period(source_raw, "starting")
    target, target_error = parse_period(target_raw, "target")

    if amount_error:
        result.errors["amount"] = amount_error
    if source_error:
        result.errors["source"] = source_error
    if target_error:
        result.errors["target"] = target_error

    if not result.errors:
        result.values = CalculationInput(amount=amount, source_period=source, target_period=target)
    return result


def equivalent_amount(amount: Decimal, source_cpi: Decimal | None, target_cpi: Decimal | None) -> tuple[Decimal, Decimal]:
    """Return (ratio, equivalent amount). Raises CalculationError for missing or invalid CPI."""
    if source_cpi is None or target_cpi is None:
        raise CalculationError("A CPI value is missing for one of the months.")
    if source_cpi <= 0 or target_cpi <= 0:
        raise CalculationError("CPI values must be positive to calculate a result.")
    ratio = (target_cpi / source_cpi).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    value = (amount * (target_cpi / source_cpi)).quantize(CENT, rounding=ROUND_HALF_UP)
    return ratio, value


def calculate(
    amount_raw: str | None,
    source_raw: str | None,
    target_raw: str | None,
) -> tuple[CalculationResult | None, dict[str, str]]:
    """Validate, look up both months, and calculate. Returns (result, field errors)."""
    validation = validate_input(amount_raw, source_raw, target_raw)
    if validation.errors:
        return None, validation.errors
    values = validation.values

    spec = get_indicator(CPI_CODE)
    points = load_points(spec)
    by_period = {point.period: point.value for point in points}
    observed = [point.period for point in points if point.value is not None]
    available_from = min(observed) if observed else None
    available_to = max(observed) if observed else None

    errors: dict[str, str] = {}
    for key, period, label in (
        ("source", values.source_period, "starting"),
        ("target", values.target_period, "target"),
    ):
        if period not in by_period:
            errors[key] = _unavailable_message(period, label, available_from, available_to)
        elif by_period[period] is None:
            errors[key] = f"The CPI value for {period.strftime('%Y-%m')} is marked as missing by the source."
    if errors:
        return None, errors

    source_cpi = by_period[values.source_period]
    target_cpi = by_period[values.target_period]
    try:
        ratio, result_amount = equivalent_amount(values.amount, source_cpi, target_cpi)
    except CalculationError as exc:
        return None, {"amount": str(exc)}

    if values.amount == 0:
        change_pct = Decimal("0.0")
    else:
        change_pct = ((result_amount - values.amount) / values.amount * Decimal(100)).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )

    result = CalculationResult(
        inputs=values,
        source_cpi=source_cpi,
        target_cpi=target_cpi,
        ratio=ratio,
        equivalent_amount=result_amount,
        change_pct=change_pct,
        snapshot=get_snapshot(CPI_CODE),
        available_from=available_from,
        available_to=available_to,
    )
    return result, {}


def _unavailable_message(period: date, label: str, first: date | None, last: date | None) -> str:
    if first is None or last is None:
        return "No CPI values are stored yet. Run the data refresh first."
    return (
        f"No CPI value is stored for {period.strftime('%Y-%m')} ({label} month). "
        f"Stored months run from {first.strftime('%Y-%m')} to {last.strftime('%Y-%m')}."
    )
