"""
smoke_test_home.py — Verifies the public homepage (the "/" route) using
Flask's test client (no real server/network needed).

Before this module, "/" always redirected straight to the login page —
a first-time visitor had no way to tell what the system was before being
asked for credentials. Now a signed-out visitor sees a homepage
explaining the system, while a signed-in visitor still goes straight to
their own dashboard exactly as before (that convenience is unchanged).

Tests:
  1. A logged-out visitor hitting "/" sees the homepage, not the login form
  2. The homepage links to the login page for both roles
  3. A logged-in student hitting "/" is still redirected to their dashboard
  4. A logged-in admin hitting "/" is still redirected to their dashboard
"""
import sys
from app import create_app

app = create_app({"TESTING": True})
client = app.test_client()

def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        global failures
        failures += 1

failures = 0

# 1. Logged-out visitor sees the homepage, not the login form
resp = client.get("/")
check("Logged-out visitor gets 200 on \"/\"", resp.status_code == 200)
check("Homepage explains the system", b"School Fees Payment Tracking" in resp.data)
check("Homepage is not the login form", b"Sign in to your account" not in resp.data)

# 2. The homepage links to the login page
check("Homepage links to the login page", b'href="/auth/login"' in resp.data)

# 3. Logged-in student is redirected straight to their dashboard, as before
client.post("/auth/login", data={
    "role": "student", "login_id": "SUMAS/2022/0697", "password": "student123"
})
resp = client.get("/", follow_redirects=True)
check("Logged-in student is redirected to their dashboard", b"Welcome, Eze Ezekiel" in resp.data)
client.get("/auth/logout")

# 4. Logged-in admin is redirected straight to their dashboard, as before
client.post("/auth/login", data={
    "role": "admin", "login_id": "ADM/001", "password": "admin123"
})
resp = client.get("/", follow_redirects=True)
check("Logged-in admin is redirected to their dashboard", b"Welcome, Ifeoma Obi" in resp.data)
client.get("/auth/logout")

print()
if failures == 0:
    print("ALL TESTS PASSED")
    sys.exit(0)
else:
    print(f"{failures} TEST(S) FAILED")
    sys.exit(1)
