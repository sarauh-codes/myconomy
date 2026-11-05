"""Economic dashboard page and its JSON series endpoint.

Inputs are checked against allow-lists (registered indicators and range keys).
Invalid input shows a message with status 400, and it never reaches the database
or causes a server error.
"""

from __future__ import annotations

from decimal import Decimal

from flask import Blueprint, jsonify, render_template, request

from ..services.dashboard_service import (
    DEFAULT_RANGE,
    RANGE_LABELS,
    RANGES,
    load_points,
    select_range,
    summarise,
)
from ..services.data_service import get_snapshot
from ..services.dataset_registry import INDICATORS

dashboard_bp = Blueprint("dashboard", __name__)

DEFAULT_INDICATOR = next(iter(INDICATORS))


def _format_value(value: Decimal | None) -> str:
    return "Not available" if value is None else f"{value:.1f}"


def _format_change(change: Decimal | None) -> str:
    if change is None:
        return "Not available"
    sign = "+" if change > 0 else ""
    return f"{sign}{change:.1f}%"


@dashboard_bp.get("/dashboard")
def dashboard():
    errors: list[str] = []

    code = request.args.get("indicator", DEFAULT_INDICATOR)
    if code not in INDICATORS:
        errors.append("That indicator is not available. Showing the default indicator.")
        code = DEFAULT_INDICATOR

    range_key = request.args.get("range", DEFAULT_RANGE)
    if range_key not in RANGES:
        errors.append("That time range is not available. Showing the default range.")
        range_key = DEFAULT_RANGE

    spec = INDICATORS[code]
    all_points = load_points(spec)
    points = select_range(all_points, range_key)
    summary = summarise(all_points, spec)
    snapshot = get_snapshot(code)

    # Newest first for the data table; the chart uses the oldest-first series.
    table_rows = [
        {"period": point.period.strftime("%Y-%m"), "value": _format_value(point.value)}
        for point in reversed(points)
    ]

    context = {
        "spec": spec,
        "indicators": [INDICATORS[key] for key in INDICATORS],
        "ranges": [(key, RANGE_LABELS[key]) for key in RANGES],
        "range_key": range_key,
        "range_label": RANGE_LABELS[range_key],
        "snapshot": snapshot,
        "summary": summary,
        "latest_value_text": _format_value(summary.latest_value),
        "latest_period_text": summary.latest_period.strftime("%Y-%m") if summary.latest_period else "Not available",
        "yoy_text": _format_change(summary.yoy_change_pct),
        "yoy_period_text": summary.yoy_period.strftime("%Y-%m") if summary.yoy_period else "",
        "mom_text": _format_change(summary.mom_change_pct),
        "mom_period_text": summary.mom_period.strftime("%Y-%m") if summary.mom_period else "",
        "table_rows": table_rows,
        "errors": errors,
        "series_url": f"/api/indicators/{code}/series?range={range_key}",
    }
    status = 400 if errors else 200
    return render_template("dashboard.html", **context), status


@dashboard_bp.get("/api/indicators/<code>/series")
def series_json(code: str):
    if code not in INDICATORS:
        return jsonify(error="Unknown indicator."), 404

    range_key = request.args.get("range", DEFAULT_RANGE)
    if range_key not in RANGES:
        return jsonify(error="Unknown range. Use one of: 1y, 5y, 10y, all."), 400

    spec = INDICATORS[code]
    snapshot = get_snapshot(code)
    points = select_range(load_points(spec), range_key)
    return jsonify(
        indicator=spec.code,
        name=spec.name,
        unit=spec.unit,
        frequency=spec.frequency,
        source_url=spec.source_url,
        range=range_key,
        status=snapshot.status,
        status_message=snapshot.status_message,
        data_as_of=snapshot.data_as_of,
        retrieved_at=snapshot.retrieved_at.isoformat() + "Z" if snapshot.retrieved_at else None,
        points=[
            {"period": point.period.isoformat(), "value": float(point.value) if point.value is not None else None}
            for point in points
        ],
    )
