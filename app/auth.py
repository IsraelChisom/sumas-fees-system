"""
auth.py — Authentication Module (Chapter 3, Section 3.3.3).

Implements:
- Functional Requirement (Student): "Log in to the system using a
  registration number and password."
- Functional Requirement (Administrator): "Log in to the system using
  a staff identifier and password."
- Non-Functional Requirement (Security): passwords are stored only as
  hashes, never plaintext; a student's session is kept strictly
  separate from an administrator's via session['user_type'].
"""
import functools
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.before_app_request
def load_logged_in_user():
    """Runs before every request: populate g.user / g.user_type from session."""
    user_type = session.get("user_type")
    user_id = session.get("user_id")
    g.user = None
    g.user_type = user_type

    if user_id is None:
        return

    db = get_db()
    if user_type == "student":
        g.user = db.execute(
            "SELECT * FROM student WHERE student_id = ?", (user_id,)
        ).fetchone()
    elif user_type == "admin":
        g.user = db.execute(
            "SELECT * FROM administrator WHERE admin_id = ?", (user_id,)
        ).fetchone()


def login_required(view):
    """Blocks access unless *any* authenticated user (student or admin)."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view(**kwargs)
    return wrapped_view


def student_required(view):
    """Blocks access unless the logged-in user is a Student.
    Enforces the Non-Functional Security Requirement: an administrator-only
    or student-only route must refuse the other role's session."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None or g.user_type != "student":
            flash("That page is only available to students.", "danger")
            return redirect(url_for("auth.login"))
        return view(**kwargs)
    return wrapped_view


def admin_required(view):
    """Blocks access unless the logged-in user is an Administrator."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None or g.user_type != "admin":
            flash("That page is only available to administrators.", "danger")
            return redirect(url_for("auth.login"))
        return view(**kwargs)
    return wrapped_view


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        login_id = request.form.get("login_id", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")  # 'student' or 'admin'

        db = get_db()
        error = None
        user = None

        if role == "student":
            user = db.execute(
                "SELECT * FROM student WHERE reg_number = ?", (login_id,)
            ).fetchone()
        else:
            user = db.execute(
                "SELECT * FROM administrator WHERE staff_id = ?", (login_id,)
            ).fetchone()

        if user is None:
            error = "Incorrect registration/staff ID or password."
        elif not check_password_hash(user["password_hash"], password):
            error = "Incorrect registration/staff ID or password."

        if error is None:
            session.clear()
            session["user_type"] = role
            session["user_id"] = user["student_id"] if role == "student" else user["admin_id"]
            flash("Logged in successfully.", "success")
            return redirect(url_for("student.dashboard" if role == "student" else "admin.dashboard"))

        flash(error, "danger")

    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


def hash_password(raw_password: str) -> str:
    return generate_password_hash(raw_password)
