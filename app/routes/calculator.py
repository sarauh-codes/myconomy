"""Purchasing power calculator page.

The form uses GET, so results can be bookmarked and shared. Nothing is saved.
Invalid input returns HTTP 400 with messages next to each field.
"""

from flask import Blueprint, render_template, request

from ..services.calculator_service import calculate
from ..services.dashboard_service import load_points
from ..services.dataset_registry import get_indicator

calculator_bp = Blueprint("calculator", __name__)

FORM_FIELDS = ("amount", "source", "target")


@calculator_bp.get("/calculator")
def calculator():
    raw = {name: request.args.get(name, "") for name in FORM_FIELDS}
    # A bare visit shows the empty form. Any submitted field triggers validation.
    submitted = any(name in request.args for name in FORM_FIELDS)

    result = None
    errors: dict[str, str] = {}
    if submitted:
        result, errors = calculate(raw["amount"], raw["source"], raw["target"])

    spec = get_indicator("cpi_headline")
    points = [p for p in load_points(spec) if p.value is not None]
    available = {
        "from": points[0].period.strftime("%Y-%m") if points else None,
        "to": points[-1].period.strftime("%Y-%m") if points else None,
    }

    context = {
        "raw": raw,
        "result": result,
        "errors": errors,
        "submitted": submitted,
        "available": available,
        "spec": spec,
    }
    status = 400 if errors else 200
    return render_template("calculator.html", **context), status
