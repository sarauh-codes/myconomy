"""Multi-indicator explorer.

Lists each registered indicator with the metadata needed to read it: unit,
geography, frequency, stored coverage, latest value, and source. Indicators are
not compared with each other, because their units and periods can differ.
"""

from flask import Blueprint, render_template

from ..services.dashboard_service import load_points
from ..services.data_service import get_snapshot
from ..services.dataset_registry import INDICATORS, format_period

explore_bp = Blueprint("explore", __name__)


@explore_bp.get("/explore")
def explore():
    rows = []
    for spec in INDICATORS.values():
        snapshot = get_snapshot(spec.code)
        observed = [p for p in load_points(spec) if p.value is not None]
        rows.append(
            {
                "code": spec.code,
                "name": spec.name,
                "description": spec.description,
                "unit": spec.unit,
                "geography": spec.geography,
                "frequency": spec.frequency.capitalize(),
                "coverage": (
                    f"{format_period(observed[0].period, spec.frequency)} to "
                    f"{format_period(observed[-1].period, spec.frequency)}"
                    if observed
                    else "No values stored yet"
                ),
                "latest": (
                    f"{snapshot.latest_value:.1f} ({format_period(snapshot.latest_period, spec.frequency)})"
                    if snapshot.latest_value is not None
                    else "Not available"
                ),
                "status": snapshot.status,
                "status_message": snapshot.status_message,
                "source_url": spec.source_url,
                "provider": spec.provider,
            }
        )
    return render_template("explore.html", rows=rows)
