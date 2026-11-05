"""Expense records: CRUD, validation, ownership, summaries, and the CPI comparison."""

from datetime import date, datetime
from decimal import Decimal

from app.extensions import db
from app.models import Expense
from app.services.data_service import refresh_indicator
from tests.helpers import StubClient, cpi_row, envelope
from tests.helpers_auth import add_expense, create_user, sign_in

NOW = datetime(2026, 11, 5, 9, 0)


def expense_form(**overrides):
    data = {"amount": "12.50", "category": "Food and drink", "month": "2026-03", "note": "lunch"}
    data.update(overrides)
    return data


def signed_in_user(client, email="alice@example.com"):
    user_id = create_user(email)
    sign_in(client, email=email)
    return user_id


def seed_cpi(app, rows):
    outcome = refresh_indicator("cpi_headline", StubClient(envelope(rows)), now=NOW)
    assert outcome.ok, outcome.message


# Creating and validating


def test_create_saves_a_record_for_the_signed_in_user(app, client):
    user_id = signed_in_user(client)
    response = client.post("/expenses", data=expense_form())
    assert response.status_code == 302
    expense = Expense.query.filter_by(user_id=user_id).one()
    assert expense.amount == Decimal("12.50")
    assert expense.expense_month == date(2026, 3, 1)
    assert expense.category == "Food and drink"
    assert expense.note == "lunch"


def test_created_record_appears_in_month_list(app, client):
    signed_in_user(client)
    client.post("/expenses", data=expense_form())
    html = client.get("/expenses?month=2026-03").get_data(as_text=True)
    assert "RM 12.50" in html
    assert "lunch" in html


def test_invalid_amounts_are_rejected(app, client):
    signed_in_user(client)
    for amount in ["-5", "abc", "1.234", ""]:
        response = client.post("/expenses", data=expense_form(amount=amount))
        assert response.status_code == 400, amount
    assert Expense.query.count() == 0


def test_future_month_is_rejected(app, client):
    signed_in_user(client)
    response = client.post("/expenses", data=expense_form(month="2099-01"))
    assert response.status_code == 400
    assert b"Choose the current month or an earlier one." in response.data


def test_invalid_month_format_is_rejected(app, client):
    signed_in_user(client)
    response = client.post("/expenses", data=expense_form(month="March 2026"))
    assert response.status_code == 400
    assert b"Use the format YYYY-MM" in response.data


def test_unknown_category_is_rejected(app, client):
    signed_in_user(client)
    response = client.post("/expenses", data=expense_form(category="Gadgets"))
    assert response.status_code == 400


def test_note_longer_than_limit_is_rejected(app, client):
    signed_in_user(client)
    response = client.post("/expenses", data=expense_form(note="x" * 201))
    assert response.status_code == 400
    assert Expense.query.count() == 0


def test_unauthenticated_create_is_redirected_to_sign_in(client):
    response = client.post("/expenses", data=expense_form())
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# Editing and deleting own records


def test_user_can_edit_their_own_record(app, client):
    user_id = signed_in_user(client)
    expense_id = add_expense(user_id, "10.00", "Transport", date(2026, 3, 1))
    response = client.post(
        f"/expenses/{expense_id}/edit",
        data=expense_form(amount="15.25", category="Transport", month="2026-02"),
    )
    assert response.status_code == 302
    updated = db.session.get(Expense, expense_id)
    assert updated.amount == Decimal("15.25")
    assert updated.expense_month == date(2026, 2, 1)


def test_user_can_delete_their_own_record(app, client):
    user_id = signed_in_user(client)
    expense_id = add_expense(user_id, "10.00", "Transport", date(2026, 3, 1))
    response = client.post(f"/expenses/{expense_id}/delete")
    assert response.status_code == 302
    assert db.session.get(Expense, expense_id) is None


def test_delete_requires_post(app, client):
    user_id = signed_in_user(client)
    expense_id = add_expense(user_id, "10.00", "Transport", date(2026, 3, 1))
    assert client.get(f"/expenses/{expense_id}/delete").status_code == 405
    assert db.session.get(Expense, expense_id) is not None


# Ownership


def test_another_users_record_is_not_visible_or_changeable(app, client):
    owner_id = create_user("owner@example.com")
    expense_id = add_expense(owner_id, "99.00", "Housing", date(2026, 3, 1), note="private note")

    # Sign in as a different user.
    signed_in_user(client, email="intruder@example.com")

    assert client.get(f"/expenses/{expense_id}/edit").status_code == 404
    assert client.post(f"/expenses/{expense_id}/edit", data=expense_form(amount="1.00")).status_code == 404
    assert client.post(f"/expenses/{expense_id}/delete").status_code == 404

    record = db.session.get(Expense, expense_id)
    assert record is not None
    assert record.amount == Decimal("99.00")
    assert record.note == "private note"


def test_another_users_records_are_not_in_my_month_list(app, client):
    owner_id = create_user("owner@example.com")
    add_expense(owner_id, "99.00", "Housing", date(2026, 3, 1), note="someone else")
    signed_in_user(client, email="intruder@example.com")
    html = client.get("/expenses?month=2026-03").get_data(as_text=True)
    assert "someone else" not in html
    assert "RM 0.00" in html


def test_nonexistent_record_is_404_like_someone_elses(app, client):
    signed_in_user(client)
    assert client.get("/expenses/999999/edit").status_code == 404


# Summaries


def test_month_summary_totals_and_category_breakdown(app, client):
    user_id = signed_in_user(client)
    add_expense(user_id, "12.50", "Food and drink", date(2026, 3, 1))
    add_expense(user_id, "7.50", "Food and drink", date(2026, 3, 1))
    add_expense(user_id, "40.00", "Transport", date(2026, 3, 1))
    add_expense(user_id, "500.00", "Housing", date(2026, 4, 1))  # different month

    html = client.get("/expenses?month=2026-03").get_data(as_text=True)
    assert "RM 60.00" in html  # total for March
    assert "3 records" in html
    assert "Transport" in html and "RM 40.00" in html
    assert "RM 20.00" in html  # food subtotal
    assert "500.00" not in html


def test_invalid_month_query_is_400(app, client):
    signed_in_user(client)
    assert client.get("/expenses?month=2026-13").status_code == 400


# CPI comparison


def test_comparison_shows_spending_and_cpi_change(app, client):
    seed_cpi(app, [cpi_row("2026-09-01", 137.6), cpi_row("2020-01-01", 126.5)])
    user_id = signed_in_user(client)
    add_expense(user_id, "100.00", "Food and drink", date(2020, 1, 1))
    add_expense(user_id, "120.00", "Food and drink", date(2026, 9, 1))

    response = client.get("/expenses/compare?from=2020-01&to=2026-09")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Change in your spending" in html
    assert "+20.0%" in html  # 100 -> 120
    assert "Change in national CPI" in html
    assert "+8.8%" in html  # 126.5 -> 137.6
    assert "indicative only" in html


def test_comparison_is_withheld_when_cpi_is_missing(app, client):
    seed_cpi(app, [cpi_row("2026-09-01", 137.6)])
    user_id = signed_in_user(client)
    add_expense(user_id, "100.00", "Food and drink", date(2020, 1, 1))
    add_expense(user_id, "120.00", "Food and drink", date(2026, 9, 1))

    html = client.get("/expenses/compare?from=2020-01&to=2026-09").get_data(as_text=True)
    assert "Comparison not available." in html
    assert "No CPI value is stored for 2020-01." in html
    assert "Change in national CPI" not in html


def test_comparison_is_withheld_when_a_month_has_no_records(app, client):
    seed_cpi(app, [cpi_row("2026-09-01", 137.6), cpi_row("2020-01-01", 126.5)])
    user_id = signed_in_user(client)
    add_expense(user_id, "120.00", "Food and drink", date(2026, 9, 1))

    html = client.get("/expenses/compare?from=2020-01&to=2026-09").get_data(as_text=True)
    assert "You have no spending records for 2020-01." in html
    assert "Change in national CPI" not in html


def test_comparison_only_uses_the_signed_in_users_records(app, client):
    seed_cpi(app, [cpi_row("2026-09-01", 137.6), cpi_row("2020-01-01", 126.5)])
    other_id = create_user("owner@example.com")
    add_expense(other_id, "100.00", "Food and drink", date(2020, 1, 1))
    add_expense(other_id, "120.00", "Food and drink", date(2026, 9, 1))
    signed_in_user(client, email="intruder@example.com")

    html = client.get("/expenses/compare?from=2020-01&to=2026-09").get_data(as_text=True)
    assert "You have no spending records for 2020-01." in html


def test_compare_page_rejects_bad_months(app, client):
    signed_in_user(client)
    response = client.get("/expenses/compare?from=2020-99&to=2026-09")
    assert response.status_code == 400
