"""Inflation alerts: rule validation, evaluation, and notifications.

Rules:
- Threshold alerts compare an index or level indicator's year-on-year change (%) with a
  threshold, above or below. Rates (unemployment, GDP growth) cannot use threshold
  alerts, because a change of a rate is not what the rule means.
- New-data alerts fire when a newer period is stored than the one the rule last saw.
- Each notification has a unique event_key. The key includes the rule, the alert type,
  the period, and (for thresholds) the value, so running the evaluation again cannot
  create a duplicate.
- Nothing is evaluated from a source whose last refresh did not succeed, so a failed
  refresh cannot create a false new-data alert.
- Inactive rules and inactive accounts are skipped.
- Each rule is committed separately, so one bad rule cannot stop the rest.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from ..extensions import db
from ..models import AlertRule, CacheEntry, Indicator, Notification, User
from ..models.alert import ALERT_TYPES, OPERATORS, period_key
from ..models.indicator import utcnow
from .dashboard_service import load_points, summarise
from .data_service import STATUS_SUCCESS
from .dataset_registry import INDICATORS, format_period, get_indicator

logger = logging.getLogger(__name__)

MAX_RULES_PER_USER = 20
THRESHOLD_MIN = Decimal("-50")
THRESHOLD_MAX = Decimal("100")


class AlertError(ValueError):
    """Invalid alert input. `errors` maps field names to messages."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("; ".join(errors.values()))
        self.errors = errors


@dataclass
class EvaluationReport:
    created: int = 0
    skipped: list[str] = field(default_factory=list)


def describe_rule(rule: AlertRule) -> str:
    if rule.alert_type == "new_data":
        return "Tell me when new data is published"
    word = "above" if rule.comparison_operator == "above" else "below"
    return f"Tell me when the 12-month change is {word} {rule.threshold_value}%"


def create_rule(
    user_id: int,
    indicator_code: str,
    alert_type: str,
    threshold_raw: str | None,
    operator: str | None,
) -> AlertRule:
    errors: dict[str, str] = {}

    if indicator_code not in INDICATORS:
        errors["indicator"] = "Choose an indicator from the list."
    if alert_type not in ALERT_TYPES:
        errors["alert_type"] = "Choose an alert type."
    if errors:
        raise AlertError(errors)

    spec = get_indicator(indicator_code)
    if AlertRule.query.filter_by(user_id=user_id).count() >= MAX_RULES_PER_USER:
        raise AlertError({"alert_type": f"You can have up to {MAX_RULES_PER_USER} alert rules."})

    indicator = Indicator.query.filter_by(code=indicator_code).first()
    if indicator is None:
        raise AlertError({"indicator": "No data has been stored for this indicator yet. Run the data refresh first."})

    threshold = None
    comparison = None
    if alert_type == "threshold":
        if not spec.shows_changes:
            raise AlertError(
                {"indicator": "Threshold alerts work with index and level indicators. This one is already a rate; use a new-data alert instead."}
            )
        try:
            threshold = Decimal((threshold_raw or "").strip())
        except InvalidOperation:
            raise AlertError({"threshold": "Enter a number, for example 3 or 2.5."}) from None
        if not threshold.is_finite() or not (THRESHOLD_MIN <= threshold <= THRESHOLD_MAX):
            raise AlertError({"threshold": f"Enter a percentage between {THRESHOLD_MIN} and {THRESHOLD_MAX}."})
        if operator not in OPERATORS:
            raise AlertError({"operator": "Choose above or below."})
        comparison = operator
        threshold = threshold.quantize(Decimal("0.01"))

    # Start from the latest stored period, so only periods published after this point alert.
    points = [p for p in load_points(spec) if p.value is not None]
    baseline = points[-1].period if points else None

    rule = AlertRule(
        user_id=user_id,
        indicator_id=indicator.id,
        alert_type=alert_type,
        threshold_value=threshold,
        comparison_operator=comparison,
        is_active=True,
        delivery_method="in_app",
        last_seen_period=baseline,
    )
    db.session.add(rule)
    db.session.commit()
    return rule


def set_active(user_id: int, rule_id: int, active: bool) -> AlertRule | None:
    rule = AlertRule.query.filter_by(id=rule_id, user_id=user_id).first()
    if rule is None:
        return None
    rule.is_active = active
    db.session.commit()
    return rule


def delete_rule(user_id: int, rule_id: int) -> bool:
    rule = AlertRule.query.filter_by(id=rule_id, user_id=user_id).first()
    if rule is None:
        return False
    db.session.delete(rule)
    db.session.commit()
    return True


def mark_read(user_id: int, notification_id: int, *, now: datetime | None = None) -> bool:
    note = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if note is None:
        return False
    if note.read_at is None:
        note.read_at = now or utcnow()
        db.session.commit()
    return True


def unread_count(user_id: int) -> int:
    return Notification.query.filter_by(user_id=user_id, read_at=None).count()


def evaluate_all(*, now: datetime | None = None) -> EvaluationReport:
    now = now or utcnow()
    report = EvaluationReport()
    rules = (
        AlertRule.query.join(User, User.id == AlertRule.user_id)
        .filter(AlertRule.is_active.is_(True), User.is_active.is_(True))
        .order_by(AlertRule.id)
        .all()
    )
    for rule in rules:
        try:
            created = evaluate_rule(rule, now=now)
            report.created += created
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("Alert rule %s could not be evaluated", rule.id)
            report.skipped.append(f"rule {rule.id}: unexpected error")
    return report


def evaluate_rule(rule: AlertRule, *, now: datetime) -> int:
    """Create any due notifications for one rule. Returns how many were created."""
    spec = get_indicator(rule.indicator.code)
    entry = CacheEntry.query.filter_by(cache_key=spec.cache_key).first()
    if entry is None or entry.status != STATUS_SUCCESS:
        logger.info("Alert rule %s skipped: the last refresh did not succeed", rule.id)
        return 0

    points = load_points(spec)
    summary = summarise(points, spec)
    if summary.latest_period is None:
        return 0

    if rule.alert_type == "new_data":
        return _evaluate_new_data(rule, spec, summary, now)
    return _evaluate_threshold(rule, spec, summary, now)


def _evaluate_new_data(rule: AlertRule, spec, summary, now: datetime) -> int:
    latest = summary.latest_period
    if rule.last_seen_period is None:
        rule.last_seen_period = latest  # first sight: set the baseline, no alert
        return 0
    if latest <= rule.last_seen_period:
        return 0

    key = f"rule:{rule.id}:new_data:{period_key(latest)}"
    created = _create_once(
        rule=rule,
        event_key=key,
        title=f"New data: {spec.name}",
        message=(
            f"{spec.name} now has a value for {format_period(latest, spec.frequency)}: "
            f"{summary.latest_value:.1f} ({spec.unit}). Source: {spec.provider}."
        ),
        period=latest,
        source_url=spec.source_url,
        now=now,
    )
    rule.last_seen_period = latest
    return created


def _evaluate_threshold(rule: AlertRule, spec, summary, now: datetime) -> int:
    change = summary.yoy_change_pct
    if change is None or rule.threshold_value is None:
        return 0  # not comparable yet: never estimate

    threshold = rule.threshold_value
    crossed = change >= threshold if rule.comparison_operator == "above" else change <= threshold
    if not crossed:
        return 0

    word = "above" if rule.comparison_operator == "above" else "below"
    period_label = format_period(summary.latest_period, spec.frequency)
    key = f"rule:{rule.id}:threshold:{period_key(summary.latest_period)}:{change}"
    return _create_once(
        rule=rule,
        event_key=key,
        title=f"Inflation alert: {spec.name}",
        message=(
            f"The 12-month change to {period_label} is {change:+.1f}%, compared with "
            f"{format_period(summary.yoy_period, spec.frequency)}. That is {word} your threshold of "
            f"{threshold}%. Source: {spec.provider}."
        ),
        period=summary.latest_period,
        source_url=spec.source_url,
        now=now,
    )


def _create_once(*, rule: AlertRule, event_key: str, title: str, message: str, period: date, source_url: str, now: datetime) -> int:
    if Notification.query.filter_by(event_key=event_key).first() is not None:
        return 0
    db.session.add(
        Notification(
            user_id=rule.user_id,
            alert_rule_id=rule.id,
            event_key=event_key,
            title=title,
            message=message,
            reference_period=period,
            source_url=source_url,
            created_at=now,
            delivery_status="delivered",
        )
    )
    return 1
