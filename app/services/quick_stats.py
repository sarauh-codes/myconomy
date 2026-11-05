"""Quick stats: the compact view of an indicator's latest cached value.

The widget reads only the cache and the stored data. It never calls the
provider, so a page view cannot be slowed down or rate-limited by OpenDOSM.
Each stat shows the value, the indicator name, the reference period, when
it was retrieved, a status, and links to the details and the source.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .data_service import get_snapshot
from .dataset_registry import INDICATORS, format_period

STATUS_TEXT = {
    "fresh": "Current",
    "stale": "Stale",
    "unavailable": "Unavailable",
}


@dataclass(frozen=True)
class QuickStat:
    code: str
    name: str
    status: str  # fresh | stale | unavailable
    status_text: str  # words shown next to the value, so status never relies on colour
    value_text: str  # "Not available" when there is no value
    unit_text: str
    period_text: str  # reference period, e.g. 2026-09 or 2026-Q2
    retrieved_text: str  # when Myconomy retrieved it (UTC)
    status_message: str
    details_url: str
    source_url: str
    provider: str


def format_value(value: Decimal | None, value_kind: str) -> str:
    if value is None:
        return "Not available"
    if value_kind == "level":
        return f"{value:,.1f}"
    return f"{value:.1f}"


def unit_suffix(value_kind: str, unit: str) -> str:
    if value_kind == "rate" and unit.startswith("per cent"):
        return "%"
    return ""


def build_quick_stat(code: str) -> QuickStat:
    spec = INDICATORS[code]
    snapshot = get_snapshot(code)
    suffix = unit_suffix(spec.value_kind, spec.unit)
    value = format_value(snapshot.latest_value, spec.value_kind)
    if snapshot.latest_value is not None and suffix:
        value = f"{value}{suffix}"
    unit_text = "" if suffix else spec.unit

    return QuickStat(
        code=spec.code,
        name=spec.name,
        status=snapshot.status,
        status_text=STATUS_TEXT.get(snapshot.status, "Unavailable"),
        value_text=value,
        unit_text=unit_text,
        period_text=(
            format_period(snapshot.latest_period, spec.frequency) if snapshot.latest_period else "Not available"
        ),
        retrieved_text=(
            snapshot.retrieved_at.strftime("%Y-%m-%d %H:%M") + " UTC" if snapshot.retrieved_at else "Not yet"
        ),
        status_message=snapshot.status_message,
        details_url=f"/dashboard?indicator={spec.code}",
        source_url=spec.source_url,
        provider=spec.provider,
    )


def home_stats() -> list[QuickStat]:
    """The indicators shown on the home page. Each must be registered."""
    return [build_quick_stat(code) for code in ("cpi_headline", "unemployment_rate", "gdp_growth_yoy")]
