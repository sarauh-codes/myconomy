"""Refresh OpenDOSM data into the database and read it back with honest status.

Rules this module enforces:
- A refresh only writes data after the whole response has validated.
- A failed or empty refresh never removes previously saved observations.
- Every snapshot carries its reference period and retrieval time, kept apart.
- Snapshots are labelled fresh, stale, or unavailable. Nothing is presented as
  live just because it was fetched recently.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from ..extensions import db
from ..models import CacheEntry, DataPoint, Indicator
from ..models.indicator import utcnow
from .dataset_registry import INDICATORS, IndicatorSpec, get_indicator
from .opendosm_client import OpenDOSMClient, OpenDOSMError
from .series_parser import Observation, ProviderMeta, parse_meta, parse_observations

logger = logging.getLogger(__name__)

STATUS_SUCCESS = "success"
STATUS_STALE = "stale"
STATUS_ERROR = "error"

SNAPSHOT_FRESH = "fresh"
SNAPSHOT_STALE = "stale"
SNAPSHOT_UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class RefreshOutcome:
    code: str
    ok: bool
    observations: int
    message: str


@dataclass(frozen=True)
class Snapshot:
    code: str
    name: str
    description: str
    unit: str
    source_url: str
    provider: str
    frequency: str
    status: str  # fresh | stale | unavailable
    status_message: str
    latest_period: date | None
    latest_value: Decimal | None
    observation_count: int
    retrieved_at: datetime | None  # when the last successful refresh finished (UTC)
    data_as_of: str | None  # provider's stated reference period
    source_last_updated: datetime | None
    source_next_update: datetime | None


def refresh_indicator(
    code: str,
    client: OpenDOSMClient,
    *,
    now: datetime | None = None,
) -> RefreshOutcome:
    """Fetch, validate, and store one indicator. Never raises for provider problems."""
    spec = get_indicator(code)
    now = now or utcnow()
    indicator = _ensure_indicator(spec)
    entry = _ensure_cache_entry(spec)

    try:
        envelope = client.fetch_series(spec.dataset_id, filter_expression=spec.filter_expression)
        observations = parse_observations(envelope, spec)
        meta = parse_meta(envelope)
    except OpenDOSMError as exc:
        return _record_failure(indicator, entry, spec, str(exc), now)
    except Exception:
        logger.exception("Unexpected error while refreshing %s", code)
        return _record_failure(indicator, entry, spec, "An unexpected error occurred during refresh.", now)

    if not observations:
        message = "The provider returned no records. The previous data was kept."
        return _record_failure(indicator, entry, spec, message, now)

    stored = _store_observations(indicator, spec, observations, now)
    _record_success(entry, spec, meta, now)
    db.session.commit()
    logger.info("Refreshed %s: %d observations stored", code, stored)
    return RefreshOutcome(code=code, ok=True, observations=len(observations), message="Refreshed successfully.")


def get_snapshot(code: str, *, now: datetime | None = None) -> Snapshot:
    """Return the latest stored data for an indicator with an honest status."""
    spec = get_indicator(code)
    now = now or utcnow()
    indicator = Indicator.query.filter_by(code=code).first()
    entry = CacheEntry.query.filter_by(cache_key=spec.cache_key).first()

    points = []
    if indicator is not None:
        points = (
            DataPoint.query.filter_by(indicator_id=indicator.id)
            .order_by(DataPoint.reference_period.desc())
            .all()
        )
    latest = next((p for p in points if p.value is not None), None)

    if not points:
        status = SNAPSHOT_UNAVAILABLE
        message = entry.last_error if entry and entry.last_error else "No data has been retrieved yet."
    elif entry and entry.status == STATUS_SUCCESS and entry.expires_at and entry.expires_at > now:
        status = SNAPSHOT_FRESH
        message = "Retrieved from OpenDOSM within the expected update window."
    else:
        status = SNAPSHOT_STALE
        if entry and entry.last_error:
            message = f"Showing the last successful data. Latest refresh: {entry.last_error}"
        else:
            message = "This data is older than expected. Refresh to check for updates."

    return Snapshot(
        code=spec.code,
        name=spec.name,
        description=spec.description,
        unit=spec.unit,
        source_url=spec.source_url,
        provider=spec.provider,
        frequency=spec.frequency,
        status=status,
        status_message=message,
        latest_period=latest.reference_period if latest else None,
        latest_value=latest.value if latest else None,
        observation_count=len(points),
        retrieved_at=entry.fetched_at if entry else None,
        data_as_of=entry.reference_period if entry else None,
        source_last_updated=entry.source_last_updated if entry else None,
        source_next_update=entry.source_next_update if entry else None,
    )


def list_snapshots(*, now: datetime | None = None) -> list[Snapshot]:
    return [get_snapshot(code, now=now) for code in INDICATORS]


# Internal helpers


def _ensure_indicator(spec: IndicatorSpec) -> Indicator:
    indicator = Indicator.query.filter_by(code=spec.code).first()
    if indicator is None:
        indicator = Indicator(code=spec.code)
        db.session.add(indicator)
    indicator.name = spec.name
    indicator.description = spec.description
    indicator.provider = spec.provider
    indicator.dataset_id = spec.dataset_id
    indicator.unit = spec.unit
    indicator.frequency = spec.frequency
    indicator.source_url = spec.source_url
    indicator.is_enabled = True
    db.session.flush()
    return indicator


def _ensure_cache_entry(spec: IndicatorSpec) -> CacheEntry:
    entry = CacheEntry.query.filter_by(cache_key=spec.cache_key).first()
    if entry is None:
        entry = CacheEntry(cache_key=spec.cache_key, status=STATUS_ERROR)
        db.session.add(entry)
        db.session.flush()
    return entry


def _store_observations(
    indicator: Indicator,
    spec: IndicatorSpec,
    observations: list[Observation],
    now: datetime,
) -> int:
    existing = {
        point.reference_period: point
        for point in DataPoint.query.filter_by(indicator_id=indicator.id, division=spec.dimension_value).all()
    }
    for observation in observations:
        point = existing.get(observation.reference_period)
        if point is None:
            point = DataPoint(
                indicator_id=indicator.id,
                reference_period=observation.reference_period,
                division=spec.dimension_value,
            )
            db.session.add(point)
        point.value = observation.value
        point.unit = spec.unit
        point.fetched_at = now
    return len(observations)


def _record_success(entry: CacheEntry, spec: IndicatorSpec, meta: ProviderMeta, now: datetime) -> None:
    entry.status = STATUS_SUCCESS
    entry.fetched_at = now
    entry.expires_at = now + timedelta(hours=spec.fresh_for_hours)
    entry.reference_period = meta.data_as_of
    entry.source_last_updated = meta.last_updated
    entry.source_next_update = meta.next_update
    entry.update_frequency = meta.update_frequency
    entry.last_attempt_at = now
    entry.last_error = None


def _record_failure(
    indicator: Indicator,
    entry: CacheEntry,
    spec: IndicatorSpec,
    message: str,
    now: datetime,
) -> RefreshOutcome:
    has_previous_data = DataPoint.query.filter_by(indicator_id=indicator.id).first() is not None
    # Keep the earlier success time and expiry, but mark the snapshot as not current.
    entry.status = STATUS_STALE if has_previous_data else STATUS_ERROR
    entry.last_attempt_at = now
    entry.last_error = message[:500]
    db.session.commit()
    logger.warning("Refresh of %s did not store data: %s", spec.code, message)
    return RefreshOutcome(code=spec.code, ok=False, observations=0, message=message)
