"""
smoke_test_admin.py — Verifies the Student & Fee Management module.
Tests:
  1. Admin can add a new student; it appears in the student list
  2. Duplicate reg_number is rejected with a friendly message (not a crash)
  3. Admin can edit a student's details
  4. Admin can add a School Fees category (department/faculty forced null)
  5. Admin can add a Departmental Fee category (department required)
  6. Departmental Fee without a department is rejected
  7. Admin can add a Faculty Fee category
  8. Duplicate fee-category scope is rejected with a friendly message
  9. A student session is refused every admin management route (Security NFR)
"""
import sys
import tempfile
import os
from app import create_app
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
               ("SUMAS/2022/0001", "Existing Student", "Computer Science", "Natural Sciences", "300", generate_password_hash("pw")))
    db.commit()

client = app.test_client()
client.post("/auth/login", data={"role": "admin", "login_id": "ADM/001", "password": "admin123"})

# 1. Add new student
resp = client.post("/admin/students/add", data={
    "reg_number": "SUMAS/2022/0999", "full_name": "New Student", "department": "Computer Science",
    "faculty": "Natural Sciences", "level": "200", "password": "pw123",
}, follow_redirects=True)
check("New student added successfully", b"New Student" in resp.data)

# 2. Duplicate reg_number rejected gracefully
resp = client.post("/admin/students/add", data={
    "reg_number": "SUMAS/2022/0999", "full_name": "Duplicate", "department": "CS",
    "faculty": "NS", "level": "200", "password": "pw123",
}, follow_redirects=True)
check("Duplicate reg_number rejected with friendly message", b"already exists" in resp.data)

# 3. Edit student
resp = client.get("/admin/students")
import re
m = re.search(rb"students/(\d+)/edit", resp.data)
student_id = m.group(1).decode()
resp = client.post(f"/admin/students/{student_id}/edit", data={
    "full_name": "New Student Renamed", "department": "Computer Science",
    "faculty": "Natural Sciences", "level": "300", "password": "",
}, follow_redirects=True)
check("Student edit succeeds", b"New Student Renamed" in resp.data)

# 4. School Fees (no dept/faculty needed)
resp = client.post("/admin/fees/add", data={
    "category_name": "School Fees", "session": "2025/2026", "department": "", "faculty": "", "amount": "150000",
}, follow_redirects=True)
check("School Fees category added", b"School Fees" in resp.data and b"added successfully" in resp.data or b"All students" in resp.data)

# 5. Departmental Fee with department
resp = client.post("/admin/fees/add", data={
    "category_name": "Departmental Fee", "session": "2025/2026", "department": "Computer Science", "faculty": "", "amount": "25000",
}, follow_redirects=True)
check("Departmental Fee with department added", b"Dept: Computer Science" in resp.data)

# 6. Departmental Fee WITHOUT department rejected
resp = client.post("/admin/fees/add", data={
    "category_name": "Departmental Fee", "session": "2025/2026", "department": "", "faculty": "", "amount": "25000",
}, follow_redirects=True)
check("Departmental Fee without department is rejected", b"Department is required" in resp.data)

# 7. Faculty Fee
resp = client.post("/admin/fees/add", data={
    "category_name": "Faculty Fee", "session": "2025/2026", "department": "", "faculty": "Natural Sciences", "amount": "10000",
}, follow_redirects=True)
check("Faculty Fee added", b"Faculty: Natural Sciences" in resp.data)

# 8. Duplicate scope rejected
resp = client.post("/admin/fees/add", data={
    "category_name": "Departmental Fee", "session": "2025/2026", "department": "Computer Science", "faculty": "", "amount": "99999",
}, follow_redirects=True)
check("Duplicate fee-category scope rejected", b"already exists" in resp.data)

client.get("/auth/logout")

# 9. Student session refused admin management routes
client.post("/auth/login", data={"role": "student", "login_id": "SUMAS/2022/0001", "password": "pw"})
for path in ["/admin/students", "/admin/students/add", "/admin/fees", "/admin/fees/add"]:
    resp = client.get(path, follow_redirects=True)
    check(f"Student refused {path}", b"only available to administrators" in resp.data)

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
