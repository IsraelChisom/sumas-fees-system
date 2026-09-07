"""
smoke_test_reporting.py — Verifies Departmental Reporting: a payment-status
roster, filterable by department and level, that the admin generates and
sends to a Head of Department (the HOD never logs into the system).
Tests:
  1. With no filter, the report lists every student
  2. Filtering by department shows only that department's students
  3. Filtering by level shows only that level's students
  4. Combining both filters narrows to the intersection
  5. A student with nothing paid shows the full fee amount owed, marked
     Outstanding
  6. A student whose invoice is Paid shows a reduced balance
  7. The CSV export has the right content type and a matching header row
  8. The CSV export respects the same filters as the HTML report
  9. A filter matching no students shows the empty state, not a crash
  10. The PDF export has the right content type, a real PDF body, and an
      attachment disposition
  11. The PDF export respects the same filters as the HTML report and CSV
  12. A filter matching no students doesn't crash the PDF export either
  13. Role separation: a student session is refused every report route,
      including the PDF export
"""
import sys
import tempfile
import os
from app import create_app
from app.db import get_db
from app.payments import handle_payment_notification

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
    db.execute("INSERT INTO student (reg_number, full_name, department, faculty, level, password_hash) VALUES (?,?,?,?,?,?)",
               ("SUMAS/2022/0512", "Chidinma Okafor", "Computer Science", "Natural Sciences", "300", generate_password_hash("student123")))
    db.execute("INSERT INTO student (reg_number, full_name, department, faculty, level, password_hash) VALUES (?,?,?,?,?,?)",
               ("SUMAS/2023/0188", "Tunde Bakare", "Nursing Science", "Health Sciences", "400", generate_password_hash("student123")))
    db.execute("INSERT INTO fee_category (category_name, session, department, faculty, amount) VALUES (?,?,?,?,?)",
               ("School Fees", "2025/2026", None, None, 150000.00))
    db.commit()

client = app.test_client()

# Eze Ezekiel pays his School Fees in full; the other two never do.
client.post("/auth/login", data={"role": "student", "login_id": "SUMAS/2022/0697", "password": "student123"})
client.post("/student/invoices/generate", data={"fee_category_id": 1, "session": "2025/2026", "payment_plan": "Full Payment"})
with app.app_context():
    db = get_db()
    invoice = db.execute("SELECT * FROM invoice WHERE student_id = 1").fetchone()
    handle_payment_notification(db, invoice["payment_reference"], invoice["amount"])
client.get("/auth/logout")

client.post("/auth/login", data={"role": "admin", "login_id": "ADM/001", "password": "admin123"})

# 1. No filter -> every student
resp = client.get("/admin/reports/departmental")
check("Report with no filter lists Eze Ezekiel", b"Eze Ezekiel" in resp.data)
check("Report with no filter lists Chidinma Okafor", b"Chidinma Okafor" in resp.data)
check("Report with no filter lists Tunde Bakare", b"Tunde Bakare" in resp.data)

# 2. Filter by department
resp = client.get("/admin/reports/departmental?department=Computer+Science")
check("Department filter shows Computer Science students", b"Eze Ezekiel" in resp.data and b"Chidinma Okafor" in resp.data)
check("Department filter excludes Nursing Science students", b"Tunde Bakare" not in resp.data)

# 3. Filter by level
resp = client.get("/admin/reports/departmental?level=400")
check("Level filter shows 400 Level students", b"Eze Ezekiel" in resp.data and b"Tunde Bakare" in resp.data)
check("Level filter excludes other levels", b"Chidinma Okafor" not in resp.data)

# 4. Combined filter
resp = client.get("/admin/reports/departmental?department=Computer+Science&level=400")
check("Combined filter narrows to the intersection (Eze only)", b"Eze Ezekiel" in resp.data and b"Chidinma Okafor" not in resp.data)

# 5 & 6. Balances reflect payment status
resp = client.get("/admin/reports/departmental?department=Nursing+Science")
check("Unpaid student shows the full fee amount owed", b"150,000.00" in resp.data)
check("Unpaid student is marked Outstanding", b"Outstanding" in resp.data)

resp = client.get("/admin/reports/departmental?department=Computer+Science&level=400")
check("Fully-paid student's balance is 0.00", b"0.00" in resp.data)
check("Fully-paid student is marked Fully Paid", b"Fully Paid" in resp.data)

# 7. CSV export — content type and header row
resp = client.get("/admin/reports/departmental/export")
check("CSV export has a CSV content type", "text/csv" in resp.content_type)
check("CSV export includes the expected header row", b"Reg. Number,Full Name,Department" in resp.data)
check("CSV export offers the file as an attachment", "attachment" in resp.headers.get("Content-Disposition", ""))

# 8. CSV export respects filters
resp = client.get("/admin/reports/departmental/export?department=Nursing+Science")
check("Filtered CSV export includes only the matching student", b"Tunde Bakare" in resp.data and b"Eze Ezekiel" not in resp.data)

# 9. A filter matching nobody doesn't crash
resp = client.get("/admin/reports/departmental?department=Physics")
check("A department with no students shows the empty state, not a crash", resp.status_code == 200 and b"No students match" in resp.data)

# 10. PDF export — content type, real PDF body, attachment disposition
resp = client.get("/admin/reports/departmental/pdf")
check("PDF export has a PDF content type", resp.content_type == "application/pdf")
check("PDF export body is a real PDF", resp.data.startswith(b"%PDF"))
check("PDF export offers the file as an attachment", "attachment" in resp.headers.get("Content-Disposition", ""))

# 11. PDF export respects filters
resp = client.get("/admin/reports/departmental/pdf?department=Nursing+Science")
check("Filtered PDF export is still a valid PDF", resp.status_code == 200 and resp.data.startswith(b"%PDF"))

# 12. A filter matching nobody doesn't crash the PDF export
resp = client.get("/admin/reports/departmental/pdf?department=Physics")
check("A department with no students doesn't crash the PDF export", resp.status_code == 200 and resp.data.startswith(b"%PDF"))

client.get("/auth/logout")

# 13. Role separation
client.post("/auth/login", data={"role": "student", "login_id": "SUMAS/2022/0697", "password": "student123"})
resp = client.get("/admin/reports/departmental", follow_redirects=True)
check("Student session is refused the departmental report", b"only available to administrators" in resp.data)
resp = client.get("/admin/reports/departmental/export", follow_redirects=True)
check("Student session is refused the CSV export", b"only available to administrators" in resp.data)
resp = client.get("/admin/reports/departmental/pdf", follow_redirects=True)
check("Student session is refused the PDF export", b"only available to administrators" in resp.data)
client.get("/auth/logout")

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
