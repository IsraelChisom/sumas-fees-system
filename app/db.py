"""
db.py — SQLite connection handling for the SUMAS Fees system.
One connection per request, opened/closed via Flask's application context
(the standard Flask pattern for sqlite3), with foreign keys enforced.
"""
import sqlite3
from flask import current_app, g

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    with current_app.open_resource("../schema.sql") as f:
        db.executescript(f.read().decode("utf8"))

def init_app(app):
    app.teardown_appcontext(close_db)
