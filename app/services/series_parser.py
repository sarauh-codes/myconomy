"""Validate and normalise an OpenDOSM series response.

Rules (violations raise MalformedResponse, so nothing partial is saved):
- Every row used by the indicator is an object with the mapped date and value fields.
- Dates are ISO dates on the first of a month (quarters start in Jan, Apr, Jul, Oct).
- Values are numbers, or null (meaning "missing"), and respect the indicator's lower bound.
  Booleans are rejected even though Python treats them as integers.
- Each period appears only once for the indicator.

Datasets can hold several series. If the indicator was fetched with a server-side
filter, every row must match it, because a mismatch means the filter was ignored.
If it was fetched without a filter, rows for other series are skipped.

An empty result is returned as an empty list. The caller decides what that means.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from .dataset_registry import IndicatorSpec
from .opendosm_client import MalformedResponse


@dataclass(frozen=True)
class Observation:
    reference_period: date
    value: Decimal | None  # None means the provider reported the value as missing


@dataclass(frozen=True)
class ProviderMeta:
    data_as_of: str | None
    last_updated: datetime | None
    next_update: datetime | None
    update_frequency: str | None


def parse_meta(envelope: dict[str, Any]) -> ProviderMeta:
    meta = envelope.get("meta", {})
    return ProviderMeta(
        data_as_of=_optional_str(meta.get("data_as_of")),
        last_updated=_optional_datetime(meta.get("last_updated")),
        next_update=_optional_datetime(meta.get("next_update")),
        update_frequency=_optional_str(meta.get("update_frequency")),
    )


def parse_observations(envelope: dict[str, Any], spec: IndicatorSpec) -> list[Observation]:
    """Return observations for this indicator, oldest first. Raises MalformedResponse on any problem."""
    rows = envelope.get("data")
    if not isinstance(rows, list):
        raise MalformedResponse("The statistics service returned an unexpected data field.")

    seen: set[date] = set()
    observations: list[Observation] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise MalformedResponse(f"Row {index} is not an object.")
        if spec.dimension_field and not _matches_dimension(row, spec, index):
            continue  # another series in the same dataset; skipped only when fetched unfiltered

        observation = _parse_row(row, spec, index)
        if observation.reference_period in seen:
            raise MalformedResponse(f"Duplicate period {observation.reference_period.isoformat()} in response.")
        seen.add(observation.reference_period)
        observations.append(observation)

    observations.sort(key=lambda item: item.reference_period)
    return observations


def _matches_dimension(row: dict[str, Any], spec: IndicatorSpec, index: int) -> bool:
    if spec.dimension_field not in row:
        raise MalformedResponse(f"Row {index} is missing the '{spec.dimension_field}' field.")
    value = row[spec.dimension_field]
    if spec.filter_expression is not None:
        # Server-side filtered: every row must match.
        if value != spec.dimension_value:
            raise MalformedResponse(
                f"Row {index} has {spec.dimension_field}={value!r}; expected {spec.dimension_value!r}."
            )
        return True
    return value == spec.dimension_value


def _parse_row(row: dict[str, Any], spec: IndicatorSpec, index: int) -> Observation:
    for field in (spec.date_field, spec.value_field):
        if field not in row:
            raise MalformedResponse(f"Row {index} is missing the '{field}' field.")

    period = _parse_period(row[spec.date_field], index)
    value = _parse_value(row[spec.value_field], spec, index)
    return Observation(reference_period=period, value=value)


def _parse_period(raw: Any, index: int) -> date:
    if not isinstance(raw, str):
        raise MalformedResponse(f"Row {index} has a non-text date.")
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise MalformedResponse(f"Row {index} has an invalid date.") from exc
    if parsed.day != 1:
        raise MalformedResponse(f"Row {index} is not on the first of the month.")
    return parsed


def _parse_value(raw: Any, spec: IndicatorSpec, index: int) -> Decimal | None:
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise MalformedResponse(f"Row {index} has a non-numeric value.")
    as_float = float(raw)
    if not math.isfinite(as_float):
        raise MalformedResponse(f"Row {index} has a non-finite value.")
    if spec.min_value is not None:
        below = as_float < spec.min_value if spec.min_inclusive else as_float <= spec.min_value
        if below:
            raise MalformedResponse(f"Row {index} is outside the plausible range for {spec.code}.")
    # Convert through str to avoid binary floating-point noise in the stored decimal.
    return Decimal(str(raw))


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _optional_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
