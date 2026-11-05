"""Personal spending summaries and the CPI comparison.

Every query is filtered by user_id, so one account can never read another's records.
The CPI comparison is indicative only. It is withheld, not estimated, when
either month has no spending records or no stored CPI value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from ..models import Expense
from .dashboard_service import load_points, percent_change
from .dataset_registry import get_indicator

CPI_CODE = "cpi_headline"


@dataclass(frozen=True)
class MonthSummary:
    month: date
    total: Decimal
    count: int
    by_category: tuple[tuple[str, Decimal], ...]


@dataclass(frozen=True)
class Comparison:
    from_summary: MonthSummary
    to_summary: MonthSummary
    spending_change_pct: Decimal | None
    cpi_change_pct: Decimal | None
    withheld_reason: str | None
    cpi_from: Decimal | None = None
    cpi_to: Decimal | None = None
    notes: list[str] = field(default_factory=list)


def expenses_for_month(user_id: int, month: date) -> list[Expense]:
    return (
        Expense.query.filter_by(user_id=user_id, expense_month=month)
        .order_by(Expense.created_at.desc(), Expense.id.desc())
        .all()
    )


def summarise_month(user_id: int, month: date) -> MonthSummary:
    rows = expenses_for_month(user_id, month)
    totals: dict[str, Decimal] = {}
    for row in rows:
        totals[row.category] = totals.get(row.category, Decimal("0.00")) + row.amount
    ordered = tuple(sorted(totals.items(), key=lambda item: item[1], reverse=True))
    return MonthSummary(
        month=month,
        total=sum((row.amount for row in rows), Decimal("0.00")),
        count=len(rows),
        by_category=ordered,
    )


def _cpi_by_period() -> dict[date, Decimal | None]:
    spec = get_indicator(CPI_CODE)
    return {point.period: point.value for point in load_points(spec)}


def compare_with_cpi(user_id: int, from_month: date, to_month: date) -> Comparison:
    """Compare spending growth between two months with the change in national CPI.

    Both months must have spending records and a stored CPI value. Otherwise
    the comparison is withheld and the reason is given.
    """
    from_summary = summarise_month(user_id, from_month)
    to_summary = summarise_month(user_id, to_month)
    cpi = _cpi_by_period()
    cpi_from = cpi.get(from_month)
    cpi_to = cpi.get(to_month)

    reasons: list[str] = []
    if from_summary.count == 0:
        reasons.append(f"You have no spending records for {from_month:%Y-%m}.")
    if to_summary.count == 0:
        reasons.append(f"You have no spending records for {to_month:%Y-%m}.")
    if from_month not in cpi or cpi_from is None:
        reasons.append(f"No CPI value is stored for {from_month:%Y-%m}.")
    if to_month not in cpi or cpi_to is None:
        reasons.append(f"No CPI value is stored for {to_month:%Y-%m}.")

    if reasons:
        return Comparison(
            from_summary=from_summary,
            to_summary=to_summary,
            spending_change_pct=None,
            cpi_change_pct=None,
            withheld_reason=" ".join(reasons),
            cpi_from=cpi_from,
            cpi_to=cpi_to,
        )

    spending_change = None
    if from_summary.total > 0:
        spending_change = percent_change(from_summary.total, to_summary.total)
    cpi_change = percent_change(cpi_from, cpi_to)

    notes = []
    if from_summary.total == 0:
        notes.append("Spending in the starting month was zero, so a percentage change cannot be calculated.")

    return Comparison(
        from_summary=from_summary,
        to_summary=to_summary,
        spending_change_pct=spending_change,
        cpi_change_pct=cpi_change,
        withheld_reason=None,
        cpi_from=cpi_from,
        cpi_to=cpi_to,
        notes=notes,
    )

