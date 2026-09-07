"""
smoke_test_pdf.py — Verifies the ReportLab PDF downloads for invoices and
receipts (app/pdf.py), the enhancement offered after every item from the
original functional-requirements list was built. These are genuine files
(Content-Disposition: attachment), not the browser's own print-to-PDF —
the existing browser-print pages stay as the default view alongside them.
Tests:
  1. Downloading an invoice PDF succeeds, with the right content type,
     a real PDF body, and an attachment disposition
  2. Downloading a receipt PDF for a paid invoice succeeds the same way
  3. Downloading a receipt PDF for an invoice that hasn't been paid yet
     is refused gracefully, not a crash
  4. Ownership: one student can't download another student's invoice or
     receipt PDF by guessing the invoice id
  5. A nonexistent invoice id is refused gracefully
  6. Role separation: an admin session is refused both PDF routes
     (they're student-only, same as the HTML views they sit beside)
  7. Logged-out sessions are redirected to login, not served a PDF
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
    db.execute("INSERT INTO fee_category (category_name, session, department, faculty, amount) VALUES (?,?,?,?,?)",
               ("School Fees", "2025/2026", None, None, 150000.00))
    db.commit()

client = app.test_client()

# Eze Ezekiel generates and pays one invoice; generates a second, unpaid one.
client.post("/auth/login", data={"role": "student", "login_id": "SUMAS/2022/0697", "password": "student123"})
client.post("/student/invoices/generate", data={"fee_category_id": 1, "session": "2025/2026", "payment_plan": "Full Payment"})
with app.app_context():
    db = get_db()
    paid_invoice = db.execute(
        "SELECT invoice.* FROM invoice JOIN student ON invoice.student_id = student.student_id "
        "WHERE student.reg_number = 'SUMAS/2022/0697'"
    ).fetchone()
    handle_payment_notification(db, paid_invoice["payment_reference"], paid_invoice["amount"])
    paid_invoice_id = paid_invoice["invoice_id"]
client.post("/student/invoices/generate", data={"fee_category_id": 1, "session": "2025/2026", "payment_plan": "First Installment"})
with app.app_context():
    db = get_db()
    unpaid_invoice = db.execute(
        "SELECT * FROM invoice WHERE invoice_id != ?", (paid_invoice_id,)
    ).fetchone()
    unpaid_invoice_id = unpaid_invoice["invoice_id"]

# 1. Invoice PDF download
resp = client.get(f"/student/invoices/{paid_invoice_id}/pdf")
check("Invoice PDF request succeeds", resp.status_code == 200)
check("Invoice PDF has the right content type", resp.content_type == "application/pdf")
check("Invoice PDF body is a real PDF", resp.data.startswith(b"%PDF"))
check("Invoice PDF is offered as an attachment", "attachment" in resp.headers.get("Content-Disposition", ""))

# 2. Receipt PDF download (paid invoice)
resp = client.get(f"/student/invoices/{paid_invoice_id}/receipt/pdf")
check("Receipt PDF request succeeds", resp.status_code == 200)
check("Receipt PDF has the right content type", resp.content_type == "application/pdf")
check("Receipt PDF body is a real PDF", resp.data.startswith(b"%PDF"))
check("Receipt PDF is offered as an attachment", "attachment" in resp.headers.get("Content-Disposition", ""))

# 3. Receipt PDF for an unpaid invoice
resp = client.get(f"/student/invoices/{unpaid_invoice_id}/receipt/pdf", follow_redirects=True)
check("Receipt PDF for an unpaid invoice is refused, not a crash", b"hasn" in resp.data and b"paid yet" in resp.data)

client.get("/auth/logout")

# 4. Ownership — Chidinma Okafor can't fetch Eze Ezekiel's PDFs
client.post("/auth/login", data={"role": "student", "login_id": "SUMAS/2022/0512", "password": "student123"})
resp = client.get(f"/student/invoices/{paid_invoice_id}/pdf", follow_redirects=True)
check("A different student is refused another student's invoice PDF", b"Invoice not found" in resp.data)
resp = client.get(f"/student/invoices/{paid_invoice_id}/receipt/pdf", follow_redirects=True)
check("A different student is refused another student's receipt PDF", b"Invoice not found" in resp.data)

# 5. Nonexistent invoice id
resp = client.get("/student/invoices/999999/pdf", follow_redirects=True)
check("A nonexistent invoice id is refused gracefully (PDF)", resp.status_code == 200 and b"Invoice not found" in resp.data)
client.get("/auth/logout")

# 6. Role separation
client.post("/auth/login", data={"role": "admin", "login_id": "ADM/001", "password": "admin123"})
resp = client.get(f"/student/invoices/{paid_invoice_id}/pdf", follow_redirects=True)
check("Admin session is refused the invoice PDF route", b"only available to students" in resp.data)
resp = client.get(f"/student/invoices/{paid_invoice_id}/receipt/pdf", follow_redirects=True)
check("Admin session is refused the receipt PDF route", b"only available to students" in resp.data)
client.get("/auth/logout")

# 7. Logged out
resp = client.get(f"/student/invoices/{paid_invoice_id}/pdf", follow_redirects=True)
check("Logged-out session is redirected to login instead of served a PDF", b"Sign in to your account" in resp.data)

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
