"""Public data status page.

Shows, for each indicator: the value, its reference period, when it was
retrieved, the provider's update schedule, the source, and an honest status.
This page is read-only. Refreshes happen through the command line.
"""

from flask import Blueprint, render_template

from ..services.data_service import list_snapshots

data_status_bp = Blueprint("data_status", __name__)


@data_status_bp.get("/data-status")
def data_status():
    return render_template("data_status.html", snapshots=list_snapshots())
