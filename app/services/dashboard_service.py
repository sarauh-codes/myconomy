"""Dashboard calculations: time ranges, period changes, and chart series.

All figures are computed from stored, validated observations. Nothing here
contains a hardcoded statistic.

Period changes are only calculated for monthly series, because the
"same month last year" and "previous month" comparisons assume one
observation per month. Other frequencies return no change figures.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from ..models import DataPoint, Indicator
from .dataset_registry import IndicatorSpec

# Range keys map to a number of monthly observations. None means all stored data.
RANGES: dict[str, int | None] = {"1y": 12, "5y": 60, "10y": 120, "all": None}
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
    yoy_period: date | None  # the same month one year earlier
    yoy_value: Decimal | None
    yoy_change_pct: Decimal | None
    mom_period: date | None  # the previous month
    mom_value: Decimal | None
    mom_change_pct: Decimal | None


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
        DataPoint.query.filter_by(indicator_id=indicator.id, division=spec.dimension_value)
        .order_by(DataPoint.reference_period.asc())
        .all()
    )
    return [Point(period=row.reference_period, value=row.value) for row in rows]


def select_range(points: list[Point], range_key: str) -> list[Point]:
    """Return the most recent points for a range key. Ranges are counted in stored months."""
    if range_key not in RANGES:
        raise KeyError(range_key)
    count = RANGES[range_key]
    if count is None or len(points) <= count:
        return list(points)
    return points[-count:]


def summarise(points: list[Point], spec: IndicatorSpec) -> PeriodSummary:
    """Latest value plus the comparisons the dashboard shows.

    The latest value is the most recent non-missing observation. Comparisons
    use the exact period one month or one year earlier, and are left empty if
    that period is missing rather than estimated.
    """
    by_period = {point.period: point.value for point in points}
    latest = next((p for p in reversed(points) if p.value is not None), None)
    if latest is None:
        return PeriodSummary(None, None, None, None, None, None, None, None)

    if spec.frequency != "MONTHLY":
        return PeriodSummary(latest.period, latest.value, None, None, None, None, None, None)

    yoy_period = shift_months(latest.period, -12)
    mom_period = shift_months(latest.period, -1)
    yoy_value = by_period.get(yoy_period)
    mom_value = by_period.get(mom_period)
    return PeriodSummary(
        latest_period=latest.period,
        latest_value=latest.value,
        yoy_period=yoy_period,
        yoy_value=yoy_value,
        yoy_change_pct=percent_change(yoy_value, latest.value),
        mom_period=mom_period,
        mom_value=mom_value,
        mom_change_pct=percent_change(mom_value, latest.value),
    )
