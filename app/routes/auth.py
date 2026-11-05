"""Registration, sign-in, sign-out, and account deletion.

Security notes:
- Passwords are hashed before they are stored, and are never logged.
- Failed sign-ins return the same message whether the email or password was wrong.
- The `next` redirect only accepts local paths, so it cannot send people to other sites.
- Every form and state-changing route is protected by a CSRF token.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..forms import DeleteAccountForm, LoginForm, RegisterForm, normalise_email
from ..models import User
from ..models.indicator import utcnow

auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15

# Checked when the email is unknown, so a missing account takes about as long to reject as a wrong password.
_DUMMY_HASH = generate_password_hash("not-the-password-of-any-account")


def _safe_next(target: str | None) -> str | None:
    """Accept only paths on this site, such as /expenses. Reject anything else."""
    if not target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return None
    return target


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("expenses.list_expenses"))

    form = RegisterForm()
    if form.validate_on_submit():
        email = normalise_email(form.email.data)
        if User.query.filter_by(email=email).first() is not None:
            # Deliberately generic, so the form does not reveal which emails are registered.
            flash("We could not create an account with those details. Try signing in, or use a different email.", "error")
            return render_template("auth/register.html", form=form), 400

        user = User(email=email, display_name=(form.display_name.data or "").strip() or None)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        logger.info("New account created (id=%s)", user.id)

        login_user(user)
        session.permanent = True
        flash("Your account is ready. Welcome to Myconomy.", "success")
        return redirect(url_for("expenses.list_expenses"))

    status = 400 if request.method == "POST" else 200
    return render_template("auth/register.html", form=form), status


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("expenses.list_expenses"))

    form = LoginForm()
    if form.validate_on_submit():
        email = normalise_email(form.email.data)
        user = User.query.filter_by(email=email).first()
        now = utcnow()
        if user is None:
            check_password_hash(_DUMMY_HASH, form.password.data)
            valid = False
        elif user.locked_until and user.locked_until > now:
            # Locked: refuse even a correct password, with the same message as any failure,
            # so the form does not reveal which accounts exist or are locked.
            check_password_hash(_DUMMY_HASH, form.password.data)
            valid = False
        else:
            valid = user.check_password(form.password.data)

        if valid and user.is_active:
            user.failed_login_count = 0
            user.locked_until = None
            db.session.commit()
            login_user(user)
            session.permanent = True
            logger.info("Signed in (id=%s)", user.id)
            return redirect(_safe_next(request.args.get("next")) or url_for("expenses.list_expenses"))

        if user is not None and not (user.locked_until and user.locked_until > now):
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= MAX_FAILED_LOGINS:
                user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
                user.failed_login_count = 0
                logger.info("Account locked after repeated failures (id=%s)", user.id)
            db.session.commit()

        logger.info("Failed sign-in attempt")
        flash(
            "Email or password is not correct. After several failed attempts, wait 15 minutes before trying again.",
            "error",
        )
        return render_template("auth/login.html", form=form), 400

    status = 400 if request.method == "POST" else 200
    return render_template("auth/login.html", form=form), status


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("You have signed out.", "success")
    return redirect(url_for("main.index"))


@auth_bp.route("/account", methods=["GET"])
@login_required
def account():
    return render_template("auth/account.html", delete_form=DeleteAccountForm(), user=current_user)


@auth_bp.post("/account/delete")
@login_required
def delete_account():
    form = DeleteAccountForm()
    if not form.validate_on_submit():
        flash("Enter your password to delete your account.", "error")
        return render_template("auth/account.html", delete_form=form, user=current_user), 400

    user = db.session.get(User, current_user.id)
    if not user.check_password(form.password.data):
        flash("That password is not correct. Your account was not deleted.", "error")
        return render_template("auth/account.html", delete_form=form, user=current_user), 400

    user_id = user.id
    # Deleting the account also deletes its expense records (cascade).
    db.session.delete(user)
    db.session.commit()
    logout_user()
    session.clear()
    logger.info("Account deleted (id=%s)", user_id)
    flash("Your account and all of its spending records have been deleted.", "success")
    return redirect(url_for("main.index"))
