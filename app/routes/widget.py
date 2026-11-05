"""Quick stats widget endpoints.

- /widget/<code>: a standalone HTML fragment of one stat, for embedding in the app.
- /api/indicators/<code>/latest: the same stat as JSON.

Both read only the cache. Neither calls the provider.
"""

from flask import Blueprint, abort, jsonify, render_template

from ..services.dataset_registry import INDICATORS
from ..services.quick_stats import build_quick_stat

widget_bp = Blueprint("widget", __name__)


@widget_bp.get("/widget/<code>")
def widget(code: str):
    if code not in INDICATORS:
        abort(404)
    return render_template("widgets/quick_stat.html", stat=build_quick_stat(code))


@widget_bp.get("/api/indicators/<code>/latest")
def latest_json(code: str):
    if code not in INDICATORS:
        return jsonify(error="Unknown indicator."), 404
    stat = build_quick_stat(code)
    return jsonify(
        indicator=stat.code,
        name=stat.name,
        status=stat.status,
        status_text=stat.status_text,
        value=stat.value_text,
        unit=stat.unit_text,
        reference_period=stat.period_text,
        retrieved_at=stat.retrieved_text,
        status_message=stat.status_message,
        details_url=stat.details_url,
        source_url=stat.source_url,
    )
