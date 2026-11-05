"""Learn & understand pages.

Each topic shows three labelled kinds of content: the explanation, an
illustrative example with invented numbers, and an official example computed
from stored OpenDOSM data. If stored data is missing, the official example says so.
"""

from __future__ import annotations

from flask import Blueprint, abort, render_template

from ..services.calculator_service import calculate
from ..services.dashboard_service import load_points, summarise
from ..services.data_service import get_snapshot
from ..services.dataset_registry import get_indicator
from ..services.learning_content import TOPICS, TOPICS_BY_SLUG

learn_bp = Blueprint("learn", __name__)


def _official_example(key: str) -> dict:
    """Return {"available": bool, "text": str, "note": str} for an official example."""
    spec = get_indicator("cpi_headline")

    if key == "cpi_latest":
        snapshot = get_snapshot("cpi_headline")
        if snapshot.latest_value is None:
            return {"available": False, "text": snapshot.status_message, "note": ""}
        period = snapshot.latest_period.strftime("%Y-%m")
        return {
            "available": True,
            "text": f"The latest stored headline CPI is {snapshot.latest_value:.1f}, for {period}.",
            "note": snapshot.status_message,
        }

    if key == "inflation_latest":
        summary = summarise(load_points(spec), spec)
        if summary.yoy_change_pct is None:
            return {
                "available": False,
                "text": "Not enough stored months to compare with a year earlier.",
                "note": "",
            }
        return {
            "available": True,
            "text": (
                f"The 12-month change to {summary.latest_period.strftime('%Y-%m')} is "
                f"{summary.yoy_change_pct:+.1f} per cent, compared with {summary.yoy_period.strftime('%Y-%m')}."
            ),
            "note": get_snapshot("cpi_headline").status_message,
        }

    if key == "purchasing_power_example":
        result, errors = calculate("100", "2020-01", "2026-09")
        if errors:
            return {"available": False, "text": " ".join(errors.values()), "note": ""}
        return {
            "available": True,
            "text": (
                f"RM 100.00 in 2020-01 is equivalent to RM {result.equivalent_amount:,.2f} in 2026-09, "
                f"using the headline CPI ({result.change_pct:+.1f} per cent)."
            ),
            "note": result.snapshot.status_message,
        }

    raise KeyError(key)


@learn_bp.get("/learn")
def learn_index():
    return render_template("learn_index.html", topics=TOPICS)


@learn_bp.get("/learn/<slug>")
def learn_topic(slug: str):
    topic = TOPICS_BY_SLUG.get(slug)
    if topic is None:
        abort(404)
    return render_template(
        "learn_topic.html",
        topic=topic,
        topics=TOPICS,
        official=_official_example(topic.official_example_key),
    )
