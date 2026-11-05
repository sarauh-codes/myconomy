"""Inflation alerts page: manage rules and read notifications. Sign-in is required."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..models import Notification
from ..services.alert_service import (
    AlertError,
    create_rule,
    delete_rule,
    describe_rule,
    mark_read,
    set_active,
    unread_count,
)
from ..models import AlertRule
from ..models.alert import ALERT_TYPES, OPERATORS
from ..services.dataset_registry import INDICATORS

alerts_bp = Blueprint("alerts", __name__, url_prefix="/alerts")


@alerts_bp.app_context_processor
def _unread_for_nav() -> dict:
    """Count unread notifications for the header badge. Anonymous visitors cost nothing."""
    if current_user.is_authenticated:
        return {"unread_alerts": unread_count(current_user.id)}
    return {"unread_alerts": 0}


def _page(errors: dict | None = None, values: dict | None = None, status: int = 200):
    rules = AlertRule.query.filter_by(user_id=current_user.id).order_by(AlertRule.id).all()
    notes = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(50)
        .all()
    )
    return (
        render_template(
            "alerts/index.html",
            rules=rules,
            notes=notes,
            indicators=list(INDICATORS.values()),
            alert_types=ALERT_TYPES,
            operators=OPERATORS,
            describe=describe_rule,
            errors=errors or {},
            values=values or {},
        ),
        status,
    )


@alerts_bp.get("")
@login_required
def index():
    return _page()


@alerts_bp.post("")
@login_required
def create():
    values = {
        "indicator": request.form.get("indicator", ""),
        "alert_type": request.form.get("alert_type", ""),
        "threshold": request.form.get("threshold", ""),
        "operator": request.form.get("operator", ""),
    }
    try:
        create_rule(
            current_user.id,
            values["indicator"],
            values["alert_type"],
            values["threshold"],
            values["operator"],
        )
    except AlertError as exc:
        return _page(errors=exc.errors, values=values, status=400)
    flash("Alert saved. You will see it in your notifications when it triggers.", "success")
    return redirect(url_for("alerts.index"))


@alerts_bp.post("/<int:rule_id>/toggle")
@login_required
def toggle(rule_id: int):
    rule = AlertRule.query.filter_by(id=rule_id, user_id=current_user.id).first()
    if rule is None:
        abort(404)
    set_active(current_user.id, rule_id, not rule.is_active)
    flash("Alert paused." if rule.is_active is False else "Alert resumed.", "success")
    return redirect(url_for("alerts.index"))


@alerts_bp.post("/<int:rule_id>/delete")
@login_required
def delete(rule_id: int):
    if not delete_rule(current_user.id, rule_id):
        abort(404)
    flash("Alert deleted.", "success")
    return redirect(url_for("alerts.index"))


@alerts_bp.post("/notifications/<int:notification_id>/read")
@login_required
def read(notification_id: int):
    if not mark_read(current_user.id, notification_id):
        abort(404)
    return redirect(url_for("alerts.index") + "#notifications")
