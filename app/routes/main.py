"""Public home page and the health check.

Both routes are open to guests. No economic figures are shown here yet:
statistics arrive with the OpenDOSM integration in Milestone 2.
"""

import logging

from flask import Blueprint, jsonify, render_template
from sqlalchemy import text

from ..extensions import db

main_bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


@main_bp.get("/")
def index():
    return render_template("index.html")


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
    return jsonify(status="ok", database="ok"), 200
