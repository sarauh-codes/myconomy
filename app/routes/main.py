"""Public home page and the health check.

Both routes are open to guests. The home page shows the latest stored figures
from the cache, so it never calls OpenDOSM directly.
"""

import logging

from flask import Blueprint, jsonify, render_template
from sqlalchemy import text

from ..extensions import db
from ..services.dataset_registry import INDICATORS
from ..services.quick_stats import build_quick_stat, home_stats

main_bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


@main_bp.get("/")
def index():
    return render_template("index.html", stats=home_stats(), indicator_count=len(INDICATORS))


@main_bp.get("/health")
def health():
    """Report whether the app and its database respond.

    Returns 503 when the database check fails, so monitoring tools can
    detect the problem. Errors are logged, but details are not returned.
    """
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check: database query failed")
        return jsonify(status="error", database="unavailable"), 503

    # Stale or unavailable data is reported, but it does not make the app unhealthy:
    # the site still works from the last good values.
    data = {code: build_quick_stat(code).status for code in INDICATORS}
    return jsonify(status="ok", database="ok", data=data), 200
