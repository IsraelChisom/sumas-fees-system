"""
smoke_test_errors.py — Verifies the custom branded 404/500 error pages
(app/__init__.py's handle_404()/handle_500(), errors/error.html), part of
the final polish pass alongside the favicon. These replace Flask's plain
default error pages so a stale link or an unexpected bug during a demo
still looks like part of the same system.

The 500 handler is exercised by calling it directly (see the module
docstring note on why: with debug=True, the dev server's Werkzeug
debugger intercepts real exceptions before this handler ever runs, and
there's no route in this app that deliberately raises one to test
against — this app has none of its own bugs to reach for).
Tests:
  1. A nonexistent URL gets the custom branded 404 page, not Flask's
     default one
  2. A logged-out visitor's 404 page points "back" at the login page
  3. A logged-in student's 404 page points "back" at their own dashboard
  4. A logged-in admin's 404 page points "back" at their own dashboard
  5. The 500 handler renders the custom branded page with a 500 status
  6. The favicon files are actually served (SVG and ICO), not a 404
"""
import sys
import tempfile
import os
from app import create_app, handle_500
from app.db import get_db

db_fd, db_path = tempfile.mkstemp()
app = create_app({"TESTING": True, "DATABASE": db_path})

failures = 0
def check(label, condition):
    global failures
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures += 1

with app.app_context():
    db = get_db()
    db.executescript(open("schema.sql").read())
    from werkzeug.security import generate_password_hash
    db.execute("INSERT INTO administrator (staff_id, full_name, password_hash) VALUES (?, ?, ?)",
               ("ADM/001", "Ifeoma Obi", generate_password_hash("admin123")))
    db.execute("INSERT INTO student (reg_number, full_name, department, faculty, level, password_hash) VALUES (?,?,?,?,?,?)",
               ("SUMAS/2022/0697", "Eze Ezekiel", "Computer Science", "Natural Sciences", "400", generate_password_hash("student123")))
    db.commit()

client = app.test_client()

# 1 & 2. Logged-out 404
resp = client.get("/this-page-does-not-exist")
check("A nonexistent URL returns a 404 status", resp.status_code == 404)
check("The 404 page is the custom branded one, not Flask's default", b"Page Not Found" in resp.data and b"SUMAS Fees System" in resp.data)
check("Logged-out 404 page points back at the login page", b'href="/auth/login"' in resp.data)

# 3. Logged-in student's 404 page
client.post("/auth/login", data={"role": "student", "login_id": "SUMAS/2022/0697", "password": "student123"})
resp = client.get("/this-page-does-not-exist")
check("Logged-in student's 404 page points back at their own dashboard", b'href="/student/dashboard"' in resp.data)
client.get("/auth/logout")

# 4. Logged-in admin's 404 page
client.post("/auth/login", data={"role": "admin", "login_id": "ADM/001", "password": "admin123"})
resp = client.get("/this-page-does-not-exist")
check("Logged-in admin's 404 page points back at their own dashboard", b'href="/admin/dashboard"' in resp.data)
client.get("/auth/logout")

# 5. The 500 handler itself, called directly (see module docstring)
with app.test_request_context("/"):
    body, status = handle_500(Exception("simulated failure"))
check("The 500 handler returns a 500 status", status == 500)
check("The 500 page is the custom branded one", "Something Went Wrong" in body and "SUMAS Fees System" in body)

# 6. Favicon files are actually served
resp = client.get("/static/favicon.svg")
check("favicon.svg is served, not a 404", resp.status_code == 200)
resp = client.get("/static/favicon.ico")
check("favicon.ico is served, not a 404", resp.status_code == 200)

print()
if failures == 0:
    print("ALL TESTS PASSED")
    os.close(db_fd)
    os.unlink(db_path)
    sys.exit(0)
else:
    print(f"{failures} TEST(S) FAILED")
    os.close(db_fd)
    os.unlink(db_path)
    sys.exit(1)
