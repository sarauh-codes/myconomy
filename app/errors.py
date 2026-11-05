"""Friendly error pages. Stack traces are logged, never shown to visitors."""

import logging

from flask import Flask, render_template
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        original = getattr(error, "original_exception", None)
        logger.error("Unhandled server error", exc_info=original)
        return render_template("errors/500.html"), 500

    @app.errorhandler(HTTPException)
    def other_http_error(error):
        # Other HTTP errors (e.g. 405) keep their status code but show a plain message.
        return render_template("errors/generic.html", error=error), error.code
