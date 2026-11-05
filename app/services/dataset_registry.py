"""Verified OpenDOSM dataset mappings.

Each entry records exactly how one indicator is read from one dataset. Field
names come from live API checks (2026-11-05), not from assumptions. Changing
a mapping is a code change that should be reviewed alongside a new live check.

Only headline CPI is registered in Milestone 2. Other indicators are added
when their own datasets are verified.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IndicatorSpec:
    code: str
    name: str
    description: str
    dataset_id: str
    provider: str
    frequency: str  # as published by the provider, e.g. MONTHLY
    unit: str
    source_url: str
    # Column that holds the period. Monthly series use the first day of the month.
    date_field: str
    # Column that holds the value for this indicator.
    value_field: str
    # Dimension column and the single value this indicator uses from it.
    dimension_field: str
    dimension_value: str
    # Lowest value that is still plausible for this indicator (exclusive).
    min_value_exclusive: float
    # How long a successful snapshot counts as fresh, in hours.
    fresh_for_hours: int
    # The verified provider query. Filters are passed as "<value>@<column>".
    filter_expression: str

    @property
    def cache_key(self) -> str:
        return f"indicator:{self.code}"


DATASET_DOC_URL = "https://developer.data.gov.my/static-api/opendosm"

INDICATORS: dict[str, IndicatorSpec] = {
    "cpi_headline": IndicatorSpec(
        code="cpi_headline",
        name="Consumer Price Index (headline)",
        description="Overall consumer price index, monthly. Used for inflation and the purchasing power calculator.",
        dataset_id="cpi_headline",
        provider="OpenDOSM",
        frequency="MONTHLY",
        # The base year is not stated in the API metadata. Left as an open
        # question so the UI never implies a base that has not been confirmed.
        unit="index points (base year not confirmed)",
        source_url=DATASET_DOC_URL,
        date_field="date",
        value_field="index",
        dimension_field="division",
        dimension_value="overall",
        min_value_exclusive=0.0,
        fresh_for_hours=12,
        filter_expression="overall@division",
    ),
}


def get_indicator(code: str) -> IndicatorSpec:
    """Return the spec for a registered indicator, or raise KeyError."""
    return INDICATORS[code]
