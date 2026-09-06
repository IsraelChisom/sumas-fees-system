"""
__init__.py — Flask application factory.
"""
import os
from datetime import datetime
from flask import Flask, redirect, render_template, session, url_for


def _home_url_and_label():
    """Where the "return" button on an error page should go, and what to
    call it — the logged-in student's/admin's own dashboard when there's a
    session, the login page otherwise. Mirrors index()'s own role check
    rather than a second copy of the routing rule."""
    if session.get("user_type") == "student":
        return url_for("student.dashboard"), "Return to your Dashboard"
    if session.get("user_type") == "admin":
        return url_for("admin.dashboard"), "Return to your Dashboard"
    return url_for("auth.login"), "Return to Login"


def handle_404(error):
    home_url, home_label = _home_url_and_label()
    return render_template(
        "errors/error.html", code=404, title="Page Not Found",
        message="The page you're looking for doesn't exist, or the link may be out of date.",
        icon="bi-signpost-split", home_url=home_url, home_label=home_label,
    ), 404


def handle_500(error):
    # A real 500 here means an unhandled exception slipped past every
    # try/except this codebase otherwise uses (see the invoice-generation
    # retry loop, the payment-matching commit/rollback) — this page is
    # the last-resort fallback, not the primary error-handling strategy.
    # Note: with `flask run`'s or run.py's debug=True, Werkzeug's
    # interactive debugger takes over and this handler is never reached —
    # it only renders when debug is off (e.g. a production-style run).
    home_url, home_label = _home_url_and_label()
    return render_template(
        "errors/error.html", code=500, title="Something Went Wrong",
        message="An unexpected error occurred on our end. Please try again, or contact the "
                "SUMAS Bursary office if the problem continues.",
        icon="bi-exclamation-octagon", home_url=home_url, home_label=home_label,
    ), 500


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev-secret-key-change-in-production",
        DATABASE=os.path.join(app.instance_path, "sumas.sqlite"),
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.update(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import db
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)

    from . import student
    app.register_blueprint(student.bp)

    from . import admin
    app.register_blueprint(admin.bp)

    app.register_error_handler(404, handle_404)
    app.register_error_handler(500, handle_500)

    @app.context_processor
    def inject_current_year():
        # Used by the login page's "© <year> SUMAS" footer note, so it
        # never goes stale — always computed, never hardcoded.
        return {"current_year": datetime.now().year}

    @app.route("/")
    def index():
        # A logged-in visitor goes straight to their own dashboard, same
        # as before. A signed-out visitor — including anyone landing on
        # the bare URL for the first time — sees the public homepage
        # instead of being dropped straight onto the login form with no
        # context for what the system is.
        if session.get("user_type") in ("student", "admin"):
            return redirect(_home_url_and_label()[0])
        return render_template("home.html")

    return app
