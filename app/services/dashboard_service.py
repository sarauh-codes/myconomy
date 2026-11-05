"""Dashboard calculations: time ranges, period changes, and chart series.

All figures are computed from stored, validated observations. Nothing here
contains a hardcoded statistic.

Changes are only calculated for index and level series, which are meaningful
to compare over time. Rate series (such as unemployment or GDP growth) are
already rates, so changes are not shown for them.

Periods are compared by calendar offset, so monthly and quarterly series use
the same rule: 12 months back for the year-on-year change, and one period
back for the change from the previous period.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from ..models import DataPoint, Indicator
from .dataset_registry import IndicatorSpec

# Range keys map to a number of years. None means all stored data.
RANGES: dict[str, int | None] = {"1y": 1, "5y": 5, "10y": 10, "all": None}
DEFAULT_RANGE = "5y"
RANGE_LABELS = {"1y": "1 year", "5y": "5 years", "10y": "10 years", "all": "All available"}

ONE_DECIMAL = Decimal("0.1")


@dataclass(frozen=True)
class Point:
    period: date
    value: Decimal | None  # None = reported as missing by the provider


@dataclass(frozen=True)
class PeriodSummary:
    latest_period: date | None
    latest_value: Decimal | None
    yoy_period: date | None  # the same period one year earlier
    yoy_value: Decimal | None
    yoy_change_pct: Decimal | None
    prev_period: date | None  # the previous period (one month or one quarter earlier)
    prev_value: Decimal | None
    prev_change_pct: Decimal | None


def shift_months(period: date, months: int) -> date:
    """Move a first-of-month date by a number of whole months."""
    total = period.year * 12 + (period.month - 1) + months
    return date(total // 12, total % 12 + 1, 1)


def percent_change(old: Decimal | None, new: Decimal | None) -> Decimal | None:
    """Percentage change from old to new, rounded to one decimal place. None if not computable."""
    if old is None or new is None or old == 0:
        return None
    return ((new - old) / old * Decimal(100)).quantize(ONE_DECIMAL, rounding=ROUND_HALF_UP)


def load_points(spec: IndicatorSpec) -> list[Point]:
    """All stored points for an indicator, oldest first."""
    indicator = Indicator.query.filter_by(code=spec.code).first()
    if indicator is None:
        return []
    rows = (
        DataPoint.query.filter_by(indicator_id=indicator.id, division=spec.storage_division)
        .order_by(DataPoint.reference_period.asc())
        .all()
    )
    return [Point(period=row.reference_period, value=row.value) for row in rows]


def select_range(points: list[Point], range_key: str, periods_per_year: int = 12) -> list[Point]:
    """Return the most recent points covering a range key, counted in years of periods."""
    if range_key not in RANGES:
        raise KeyError(range_key)
    years = RANGES[range_key]
    if years is None:
        return list(points)
    count = years * periods_per_year
    if len(points) <= count:
        return list(points)
    return points[-count:]


def summarise(points: list[Point], spec: IndicatorSpec) -> PeriodSummary:
    """Latest value plus the comparisons the dashboard shows, when they apply.

    The latest value is the most recent non-missing observation. Comparisons
    use the exact period before, and are left empty if that period is missing
    rather than estimated. Rate series return the latest value only.
    """
    by_period = {point.period: point.value for point in points}
    latest = next((p for p in reversed(points) if p.value is not None), None)
    if latest is None:
        return PeriodSummary(None, None, None, None, None, None, None, None)

    if not spec.shows_changes:
        return PeriodSummary(latest.period, latest.value, None, None, None, None, None, None)

    step = 12 // spec.periods_per_year
    yoy_period = shift_months(latest.period, -12)
    prev_period = shift_months(latest.period, -step)
    yoy_value = by_period.get(yoy_period)
    prev_value = by_period.get(prev_period)
    return PeriodSummary(
        latest_period=latest.period,
        latest_value=latest.value,
        yoy_period=yoy_period,
        yoy_value=yoy_value,
        yoy_change_pct=percent_change(yoy_value, latest.value),
        prev_period=prev_period,
        prev_value=prev_value,
        prev_change_pct=percent_change(prev_value, latest.value),
    )
