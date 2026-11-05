"""Unit tests for dashboard calculations. Pure functions only; no database."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from app.services.dashboard_service import (
    Point,
    percent_change,
    select_range,
    shift_months,
    summarise,
)
from app.services.dataset_registry import INDICATORS

SPEC = INDICATORS["cpi_headline"]


def monthly(start: date, values: list) -> list[Point]:
    return [Point(period=shift_months(start, i), value=None if v is None else Decimal(str(v))) for i, v in enumerate(values)]


@pytest.mark.parametrize(
    "start, months, expected",
    [
        (date(2026, 9, 1), -1, date(2026, 8, 1)),
        (date(2026, 9, 1), -12, date(2025, 9, 1)),
        (date(2026, 1, 1), -1, date(2025, 12, 1)),
        (date(2026, 12, 1), 1, date(2027, 1, 1)),
        (date(2026, 9, 1), -120, date(2016, 9, 1)),
    ],
)
def test_shift_months_crosses_year_boundaries(start, months, expected):
    assert shift_months(start, months) == expected


def test_percent_change_is_rounded_to_one_decimal():
    assert percent_change(Decimal("100"), Decimal("112.5")) == Decimal("12.5")
    assert percent_change(Decimal("137.5"), Decimal("137.6")) == Decimal("0.1")


def test_percent_change_is_none_when_not_computable():
    assert percent_change(None, Decimal("1")) is None
    assert percent_change(Decimal("1"), None) is None
    assert percent_change(Decimal("0"), Decimal("1")) is None  # avoids division by zero


def test_summary_compares_with_same_month_last_year_and_previous_month():
    # 13 consecutive months: Sep 2025 .. Sep 2026, value rises by 1 each month.
    points = monthly(date(2025, 9, 1), [100 + i for i in range(13)])
    summary = summarise(points, SPEC)

    assert summary.latest_period == date(2026, 9, 1)
    assert summary.latest_value == Decimal("112")
    assert summary.yoy_period == date(2025, 9, 1)
    assert summary.yoy_value == Decimal("100")
    assert summary.yoy_change_pct == Decimal("12.0")
    assert summary.prev_period == date(2026, 8, 1)
    assert summary.prev_change_pct == Decimal("0.9")


def test_summary_leaves_changes_empty_when_comparison_month_is_missing():
    # Aug 2026 = 137.5, Sep 2026 missing, Oct 2026 = 137.6. The series has no Oct 2025 value.
    points = monthly(date(2026, 8, 1), [137.5, None, 137.6])
    summary = summarise(points, SPEC)
    assert summary.latest_period == date(2026, 10, 1)
    assert summary.latest_value == Decimal("137.6")
    assert summary.yoy_change_pct is None  # Oct 2025 is not stored
    assert summary.prev_change_pct is None  # Sep 2026 is missing, so nothing is estimated


def test_latest_value_skips_trailing_missing_observations():
    points = monthly(date(2026, 7, 1), [137.2, 137.5, None])
    summary = summarise(points, SPEC)
    assert summary.latest_period == date(2026, 8, 1)
    assert summary.latest_value == Decimal("137.5")


def test_summary_is_empty_without_any_value():
    summary = summarise([], SPEC)
    assert summary.latest_period is None
    assert summary.latest_value is None


def test_quarterly_index_compares_four_quarters_and_one_quarter_back():
    quarterly = replace(SPEC, frequency="QUARTERLY")
    # Quarter starts: Jan 2025, Apr 2025, Jul 2025, Oct 2025, Jan 2026
    points = [
        Point(date(2025, 1, 1), Decimal("100")),
        Point(date(2025, 4, 1), Decimal("101")),
        Point(date(2025, 7, 1), Decimal("102")),
        Point(date(2025, 10, 1), Decimal("103")),
        Point(date(2026, 1, 1), Decimal("104")),
    ]
    summary = summarise(points, quarterly)
    assert summary.latest_period == date(2026, 1, 1)
    assert summary.yoy_period == date(2025, 1, 1)
    assert summary.yoy_change_pct == Decimal("4.0")
    assert summary.prev_period == date(2025, 10, 1)
    assert summary.prev_change_pct == Decimal("1.0")


def test_rate_series_show_latest_value_but_no_changes():
    rate = replace(SPEC, value_kind="rate", frequency="MONTHLY")
    points = monthly(date(2025, 9, 1), [3.0 + i * 0.1 for i in range(13)])
    summary = summarise(points, rate)
    assert summary.latest_value is not None
    assert summary.yoy_change_pct is None
    assert summary.prev_change_pct is None


def test_select_range_takes_most_recent_months():
    points = monthly(date(2020, 1, 1), [float(i) for i in range(100)])
    assert len(select_range(points, "1y")) == 12
    assert len(select_range(points, "5y")) == 60
    assert select_range(points, "5y")[-1] == points[-1]
    assert len(select_range(points, "all")) == 100


def test_select_range_returns_everything_when_history_is_short():
    points = monthly(date(2026, 1, 1), [1.0, 2.0])
    assert select_range(points, "10y") == points


def test_select_range_rejects_unknown_key():
    with pytest.raises(KeyError):
        select_range([], "forever")
