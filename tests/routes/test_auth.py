"""Registration, sign-in, sign-out, account deletion, access control, and CSRF."""

from app.extensions import db
from app.models import Expense, User
from tests.helpers_auth import PASSWORD, add_expense, create_user, csrf_token_from, sign_in

from datetime import date

REGISTER = {
    "email": "New.User@Example.com",
    "display_name": "New",
    "password": PASSWORD,
    "confirm": PASSWORD,
}


def test_register_stores_a_hash_not_the_password(app, client):
    response = client.post("/register", data=REGISTER)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/expenses")

    user = User.query.filter_by(email="new.user@example.com").one()
    assert user.password_hash != PASSWORD
    assert PASSWORD not in user.password_hash
    assert user.check_password(PASSWORD)


def test_register_signs_the_user_in(app, client):
    client.post("/register", data=REGISTER)
    assert client.get("/expenses").status_code == 200


def test_register_rejects_short_passwords(app, client):
    response = client.post("/register", data={**REGISTER, "password": "short", "confirm": "short"})
    assert response.status_code == 400
    assert b"Use at least 12 characters." in response.data
    assert User.query.count() == 0


def test_register_rejects_mismatched_confirmation(app, client):
    response = client.post("/register", data={**REGISTER, "confirm": PASSWORD + "x"})
    assert response.status_code == 400
    assert b"The passwords do not match." in response.data


def test_register_rejects_invalid_email(app, client):
    response = client.post("/register", data={**REGISTER, "email": "not-an-email"})
    assert response.status_code == 400
    assert b"Enter a valid email address." in response.data


def test_duplicate_registration_gives_a_generic_message(app, client):
    create_user("new.user@example.com")
    response = client.post("/register", data=REGISTER)
    assert response.status_code == 400
    assert b"We could not create an account with those details." in response.data
    assert User.query.count() == 1


def test_login_success_redirects_to_expenses(app, client):
    create_user()
    response = sign_in(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/expenses")


def test_wrong_password_and_unknown_email_give_the_same_message(app, client):
    create_user()
    wrong_password = sign_in(client, password="not-the-password-at-all")
    unknown_email = sign_in(client, email="nobody@example.com")
    assert wrong_password.status_code == unknown_email.status_code == 400
    assert b"Email or password is not correct." in wrong_password.data
    assert b"Email or password is not correct." in unknown_email.data


def test_login_redirects_to_a_local_next_page_only(app, client):
    create_user()
    response = client.post("/login?next=/calculator", data={"email": "alice@example.com", "password": PASSWORD})
    assert response.headers["Location"].endswith("/calculator")


def test_login_ignores_external_next_targets(app, client):
    create_user()
    for target in ["https://evil.example/steal", "//evil.example", "/\\evil.example"]:
        client.get("/logout")  # ensure a clean state between attempts
        response = client.post(f"/login?next={target}", data={"email": "alice@example.com", "password": PASSWORD})
        assert "evil.example" not in response.headers["Location"], target


def test_protected_pages_redirect_to_sign_in(client):
    response = client.get("/expenses")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert client.get("/account").status_code == 302


def test_logout_requires_post(app, client):
    create_user()
    sign_in(client)
    assert client.get("/logout").status_code == 405


def test_logout_ends_the_session(app, client):
    create_user()
    sign_in(client)
    client.post("/logout")
    assert client.get("/expenses").status_code == 302


def test_public_pages_do_not_need_an_account(client):
    for path in ["/", "/dashboard", "/calculator", "/learn", "/learn/cpi", "/explore", "/data-status"]:
        assert client.get(path).status_code == 200, path


def test_account_page_shows_email_but_not_password_hash(app, client):
    create_user()
    sign_in(client)
    html = client.get("/account").get_data(as_text=True)
    assert "alice@example.com" in html
    assert "scrypt:" not in html and "pbkdf2:" not in html


def test_delete_account_needs_the_correct_password(app, client):
    user_id = create_user()
    add_expense(user_id, "10.00", "Food and drink", date(2026, 3, 1))
    sign_in(client)

    response = client.post("/account/delete", data={"password": "wrong-password-here"})
    assert response.status_code == 400
    assert db.session.get(User, user_id) is not None
    assert Expense.query.filter_by(user_id=user_id).count() == 1


def test_delete_account_removes_the_user_and_all_their_records(app, client):
    user_id = create_user()
    other_id = create_user("bob@example.com")
    add_expense(user_id, "10.00", "Food and drink", date(2026, 3, 1))
    add_expense(user_id, "20.00", "Transport", date(2026, 4, 1))
    add_expense(other_id, "5.00", "Other", date(2026, 3, 1))
    sign_in(client)

    response = client.post("/account/delete", data={"password": PASSWORD})
    assert response.status_code == 302
    assert db.session.get(User, user_id) is None
    assert Expense.query.filter_by(user_id=user_id).count() == 0
    # Another user's records are untouched.
    assert Expense.query.filter_by(user_id=other_id).count() == 1


def test_csrf_protects_sign_in_when_enabled(app, client):
    create_user()
    app.config["WTF_CSRF_ENABLED"] = True
    response = client.post("/login", data={"email": "alice@example.com", "password": PASSWORD})
    assert response.status_code == 400
    assert b"CSRF" in response.data


def test_csrf_protects_sign_out_when_enabled(app, client):
    create_user()
    sign_in(client)  # sign in with CSRF disabled
    app.config["WTF_CSRF_ENABLED"] = True
    response = client.post("/logout")
    assert response.status_code == 400


def test_forms_include_a_csrf_token_when_enabled(app, client):
    app.config["WTF_CSRF_ENABLED"] = True
    html = client.get("/login").get_data(as_text=True)
    assert 'name="csrf_token"' in html
    token = csrf_token_from(html)
    create_user()
    response = client.post(
        "/login",
        data={"email": "alice@example.com", "password": PASSWORD, "csrf_token": token},
    )
    assert response.status_code == 302
