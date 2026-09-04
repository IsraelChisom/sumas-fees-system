"""
smoke_test_auth.py — Verifies the Authentication Module end-to-end using
Flask's test client (no real server/network needed).
Tests:
  1. Student login with correct credentials succeeds -> dashboard
  2. Admin login with correct credentials succeeds -> dashboard
  3. Wrong password is rejected
  4. A student session cannot access an admin-only route (Security NFR)
  5. An admin session cannot access a student-only route
  6. Logout clears the session
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

# 1. Student login
resp = client.post("/auth/login", data={
    "role": "student", "login_id": "SUMAS/2022/0697", "password": "student123"
}, follow_redirects=True)
check("Student login succeeds and reaches dashboard", b"Welcome, Eze Ezekiel" in resp.data)

client.get("/auth/logout")

# 2. Admin login
resp = client.post("/auth/login", data={
    "role": "admin", "login_id": "ADM/001", "password": "admin123"
}, follow_redirects=True)
check("Admin login succeeds and reaches dashboard", b"Welcome, Ifeoma Obi" in resp.data)

client.get("/auth/logout")

# 3. Wrong password rejected
resp = client.post("/auth/login", data={
    "role": "student", "login_id": "SUMAS/2022/0697", "password": "wrongpass"
}, follow_redirects=True)
check("Wrong password is rejected", b"Incorrect registration/staff ID or password" in resp.data)

# 4. Student session cannot access admin dashboard (Security NFR)
client.post("/auth/login", data={
    "role": "student", "login_id": "SUMAS/2022/0697", "password": "student123"
})
resp = client.get("/admin/dashboard", follow_redirects=True)
check("Student session is refused admin dashboard", b"only available to administrators" in resp.data)
client.get("/auth/logout")

# 5. Admin session cannot access student dashboard
client.post("/auth/login", data={
    "role": "admin", "login_id": "ADM/001", "password": "admin123"
})
resp = client.get("/student/dashboard", follow_redirects=True)
check("Admin session is refused student dashboard", b"only available to students" in resp.data)

# 6. Logout clears session
client.get("/auth/logout")
resp = client.get("/admin/dashboard", follow_redirects=True)
check("Logged-out session is redirected to login", b"Log in" in resp.data and b"Welcome, Ifeoma Obi" not in resp.data)

print()
if failures == 0:
    print("ALL TESTS PASSED")
    sys.exit(0)
else:
    print(f"{failures} TEST(S) FAILED")
    sys.exit(1)
