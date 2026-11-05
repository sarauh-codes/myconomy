"""Verified OpenDOSM dataset mappings.

Each entry records exactly how one indicator is read from one dataset. Field
names, dimensions, and units come from live API checks (verified 2026-11-05),
not from assumptions. Changing a mapping is a code change that should be
reviewed alongside a new live check.

Units that the API does not state are labelled as inferred or unconfirmed.
Population is not registered yet: it needs a national total summed from states.
"""

from __future__ import annotations

from dataclasses import dataclass

DATASET_DOC_URL = "https://developer.data.gov.my/static-api/opendosm"
NATIONAL = "Malaysia (national)"

PERIODS_PER_YEAR = {"MONTHLY": 12, "QUARTERLY": 4, "YEARLY": 1}


@dataclass(frozen=True)
class IndicatorSpec:
    code: str
    name: str
    description: str
    dataset_id: str
    provider: str
    frequency: str  # MONTHLY, QUARTERLY, or YEARLY, as published by the provider
    unit: str
    geography: str
    source_url: str
    # index: a price index (changes are meaningful).
    # level: an absolute amount (changes are meaningful).
    # rate: a percentage that is already a rate of change or share (no changes shown).
    value_kind: str
    value_field: str
    date_field: str = "date"
    # Rows are selected by this column and value when the dataset holds several series.
    dimension_field: str | None = None
    dimension_value: str | None = None
    # Lower bound for plausible values. None means no bound.
    min_value: float | None = None
    min_inclusive: bool = False
    # Server-side filter, passed as "<value>@<column>". None means no server filter.
    filter_expression: str | None = None
    # How long a successful snapshot counts as fresh, in hours.
    fresh_for_hours: int = 12

    @property
    def cache_key(self) -> str:
        return f"indicator:{self.code}"

    @property
    def fetch_key(self) -> tuple[str, str | None]:
        """Indicators with the same key can share one provider request."""
        return (self.dataset_id, self.filter_expression)

    @property
    def storage_division(self) -> str:
        """Value stored in data_points.division for this indicator's rows."""
        return self.dimension_value or ""

    @property
    def periods_per_year(self) -> int:
        return PERIODS_PER_YEAR[self.frequency]

    @property
    def shows_changes(self) -> bool:
        return self.value_kind in ("index", "level")


INDICATORS: dict[str, IndicatorSpec] = {
    "cpi_headline": IndicatorSpec(
        code="cpi_headline",
        name="Consumer Price Index (headline)",
        description="Overall consumer price index, monthly. Used for inflation and the purchasing power calculator.",
        dataset_id="cpi_headline",
        provider="OpenDOSM",
        frequency="MONTHLY",
        # The base year is not stated in the API metadata.
        unit="index points (base year not confirmed)",
        geography=NATIONAL,
        source_url=DATASET_DOC_URL,
        value_kind="index",
        value_field="index",
        dimension_field="division",
        dimension_value="overall",
        min_value=0.0,
        min_inclusive=False,
        filter_expression="overall@division",
        fresh_for_hours=12,
    ),
    "gdp_real_level": IndicatorSpec(
        code="gdp_real_level",
        name="Real gross domestic product (level)",
        description=(
            "Real GDP for each quarter. The dataset also holds growth series, which are shown as separate indicators."
        ),
        dataset_id="gdp_qtr_real",
        provider="OpenDOSM",
        frequency="QUARTERLY",
        # The API does not state the unit. The magnitude suggests RM million; the price base is unconfirmed.
        unit="RM million, real terms (inferred; price base unconfirmed)",
        geography=NATIONAL,
        source_url=DATASET_DOC_URL,
        value_kind="level",
        value_field="value",
        dimension_field="series",
        dimension_value="abs",
        min_value=0.0,
        min_inclusive=False,
        filter_expression=None,
        fresh_for_hours=24,
    ),
    "gdp_growth_yoy": IndicatorSpec(
        code="gdp_growth_yoy",
        name="Real GDP growth, year on year",
        description="Change in real GDP compared with the same quarter a year earlier.",
        dataset_id="gdp_qtr_real",
        provider="OpenDOSM",
        frequency="QUARTERLY",
        unit="per cent",
        geography=NATIONAL,
        source_url=DATASET_DOC_URL,
        value_kind="rate",
        value_field="value",
        dimension_field="series",
        dimension_value="growth_yoy",
        min_value=None,  # growth can be negative
        filter_expression=None,
        fresh_for_hours=24,
    ),
    "unemployment_rate": IndicatorSpec(
        code="unemployment_rate",
        name="Unemployment rate",
        description="Unemployed people as a share of the labour force, monthly.",
        dataset_id="lfs_month",
        provider="OpenDOSM",
        frequency="MONTHLY",
        # Checked against the other fields: u_rate equals lf_unemployed ÷ lf × 100 in the sample rows.
        unit="per cent of the labour force",
        geography=NATIONAL,
        source_url=DATASET_DOC_URL,
        value_kind="rate",
        value_field="u_rate",
        min_value=0.0,
        min_inclusive=True,
        filter_expression=None,
        fresh_for_hours=12,
    ),
}


def get_indicator(code: str) -> IndicatorSpec:
    """Return the spec for a registered indicator, or raise KeyError."""
    return INDICATORS[code]


def format_period(period, frequency: str) -> str:
    """Human label for a period: 2026-09, 2026-Q2, or 2023."""
    if frequency == "QUARTERLY":
        return f"{period.year}-Q{(period.month - 1) // 3 + 1}"
    if frequency == "YEARLY":
        return str(period.year)
    return period.strftime("%Y-%m")
