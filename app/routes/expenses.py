"""Personal cost-of-living tracker: monthly expense records and the CPI comparison.

Every route requires sign-in. Records are looked up by both id and owner, so a
record that belongs to someone else returns 404, the same as one that does not exist.
"""

from __future__ import annotations

from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import CATEGORIES, ExpenseForm, parse_expense_amount, parse_month
from ..models import Expense
from ..services.expense_service import compare_with_cpi, expenses_for_month, summarise_month

expenses_bp = Blueprint("expenses", __name__, url_prefix="/expenses")


@expenses_bp.app_context_processor
def _category_choices() -> dict:
    return {"categories": CATEGORIES}


def _current_month() -> date:
    today = date.today()
    return date(today.year, today.month, 1)


def _owned_expense_or_404(expense_id: int) -> Expense:
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first()
    if expense is None:
        abort(404)
    return expense


def _fill_from_form(form: ExpenseForm, expense: Expense) -> tuple[bool, str | None]:
    """Validate the form and copy values onto the expense. Returns (ok, message)."""
    try:
        amount = parse_expense_amount(form.amount.data)
    except ValueError as exc:
        form.amount.errors.append(str(exc))
        return False, None
    try:
        month = parse_month(form.month.data)
    except ValueError as exc:
        form.month.errors.append(str(exc))
        return False, None
    if form.category.data not in CATEGORIES:
        form.category.errors.append("Choose a category from the list.")
        return False, None

    expense.amount = amount
    expense.expense_month = month
    expense.category = form.category.data
    expense.note = (form.note.data or "").strip() or None
    return True, None


@expenses_bp.get("")
@login_required
def list_expenses():
    raw_month = request.args.get("month")
    error = None
    if raw_month:
        try:
            month = parse_month(raw_month)
        except ValueError as exc:
            error = str(exc)
            month = _current_month()
    else:
        month = _current_month()

    form = ExpenseForm(month=month.strftime("%Y-%m"))
    summary = summarise_month(current_user.id, month)
    rows = expenses_for_month(current_user.id, month)
    context = {
        "form": form,
        "month": month,
        "month_value": month.strftime("%Y-%m"),
        "summary": summary,
        "rows": rows,
        "month_error": error,
        "current_month_value": _current_month().strftime("%Y-%m"),
    }
    status = 400 if error else 200
    return render_template("expenses/list.html", **context), status


@expenses_bp.post("")
@login_required
def create_expense():
    form = ExpenseForm()
    expense = Expense(user_id=current_user.id)
    ok, _ = _fill_from_form(form, expense) if form.validate_on_submit() else (False, None)
    if not ok:
        month = _current_month()
        summary = summarise_month(current_user.id, month)
        rows = expenses_for_month(current_user.id, month)
        return render_template(
            "expenses/list.html",
            form=form,
            month=month,
            month_value=month.strftime("%Y-%m"),
            summary=summary,
            rows=rows,
            month_error=None,
            current_month_value=_current_month().strftime("%Y-%m"),
        ), 400

    db.session.add(expense)
    db.session.commit()
    flash("Expense saved.", "success")
    return redirect(url_for("expenses.list_expenses", month=expense.expense_month.strftime("%Y-%m")))


@expenses_bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id: int):
    expense = _owned_expense_or_404(expense_id)

    if request.method == "GET":
        form = ExpenseForm(
            amount=f"{expense.amount:.2f}",
            category=expense.category,
            month=expense.expense_month.strftime("%Y-%m"),
            note=expense.note or "",
        )
        return render_template("expenses/edit.html", form=form, expense=expense)

    form = ExpenseForm()
    if not form.validate_on_submit():
        return render_template("expenses/edit.html", form=form, expense=expense), 400
    ok, _ = _fill_from_form(form, expense)
    if not ok:
        return render_template("expenses/edit.html", form=form, expense=expense), 400

    db.session.commit()
    flash("Expense updated.", "success")
    return redirect(url_for("expenses.list_expenses", month=expense.expense_month.strftime("%Y-%m")))


@expenses_bp.post("/<int:expense_id>/delete")
@login_required
def delete_expense(expense_id: int):
    expense = _owned_expense_or_404(expense_id)
    month_value = expense.expense_month.strftime("%Y-%m")
    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted.", "success")
    return redirect(url_for("expenses.list_expenses", month=month_value))


@expenses_bp.get("/compare")
@login_required
def compare():
    raw_from = request.args.get("from", "")
    raw_to = request.args.get("to", "")
    if not raw_from and not raw_to:
        return render_template("expenses/compare.html", comparison=None, errors={}, raw_from="", raw_to="")

    errors: dict[str, str] = {}
    from_month = to_month = None
    try:
        from_month = parse_month(raw_from)
    except ValueError as exc:
        errors["from"] = str(exc)
    try:
        to_month = parse_month(raw_to)
    except ValueError as exc:
        errors["to"] = str(exc)
    if errors:
        return render_template("expenses/compare.html", comparison=None, errors=errors, raw_from=raw_from, raw_to=raw_to), 400

    comparison = compare_with_cpi(current_user.id, from_month, to_month)
    return render_template(
        "expenses/compare.html",
        comparison=comparison,
        errors={},
        raw_from=raw_from,
        raw_to=raw_to,
    )
