"""
smoke_test_search.py — Verifies Search Payment Records: an admin lookup of
invoices by student (name or reg. number) or payment reference, optionally
narrowed by status. This is the last item from the original
functional-requirements list.
Tests:
  1. Searching by reg. number finds that student's invoice
  2. Searching by full name finds that student's invoice
  3. Searching by payment reference finds the matching invoice
  4. A search matching nobody shows the empty state, not a crash
  5. Filtering by status = Paid excludes an Awaiting Payment invoice
  6. Filtering by status = Awaiting Payment excludes a Paid invoice
  7. With no filters at all, every invoice is listed
  8. A paid invoice's row shows its receipt number
  9. Role separation: a student session is refused the search route
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

# Eze Ezekiel generates and pays an invoice; Chidinma Okafor generates one
# and leaves it unpaid.
client.post("/auth/login", data={"role": "student", "login_id": "SUMAS/2022/0697", "password": "student123"})
client.post("/student/invoices/generate", data={"fee_category_id": 1, "payment_plan": "Full Payment"})
with app.app_context():
    db = get_db()
    eze_invoice = db.execute(
        "SELECT invoice.* FROM invoice JOIN student ON invoice.student_id = student.student_id "
        "WHERE student.reg_number = 'SUMAS/2022/0697'"
    ).fetchone()
    handle_payment_notification(db, eze_invoice["payment_reference"], eze_invoice["amount"])
    eze_reference = eze_invoice["payment_reference"]
client.get("/auth/logout")

client.post("/auth/login", data={"role": "student", "login_id": "SUMAS/2022/0512", "password": "student123"})
client.post("/student/invoices/generate", data={"fee_category_id": 1, "payment_plan": "Full Payment"})
client.get("/auth/logout")

client.post("/auth/login", data={"role": "admin", "login_id": "ADM/001", "password": "admin123"})

# 1. Search by reg. number
resp = client.get("/admin/payments/search?q=SUMAS/2022/0697")
check("Search by reg. number finds Eze Ezekiel's invoice", b"Eze Ezekiel" in resp.data)
check("Search by reg. number excludes Chidinma Okafor", b"Chidinma Okafor" not in resp.data)

# 2. Search by full name
resp = client.get("/admin/payments/search?q=Chidinma")
check("Search by name finds Chidinma Okafor's invoice", b"Chidinma Okafor" in resp.data)
check("Search by name excludes Eze Ezekiel", b"Eze Ezekiel" not in resp.data)

# 3. Search by payment reference
resp = client.get(f"/admin/payments/search?q={eze_reference}")
check("Search by payment reference finds the matching invoice", b"Eze Ezekiel" in resp.data)

# 4. No matches
resp = client.get("/admin/payments/search?q=Nonexistent+Student")
check("A search matching nobody shows the empty state, not a crash", resp.status_code == 200 and b"No payment records match" in resp.data)

# 5 & 6. Status filter
resp = client.get("/admin/payments/search?status=Paid")
check("Status=Paid shows Eze Ezekiel (paid)", b"Eze Ezekiel" in resp.data)
check("Status=Paid excludes Chidinma Okafor (awaiting)", b"Chidinma Okafor" not in resp.data)

resp = client.get("/admin/payments/search?status=Awaiting+Payment")
check("Status=Awaiting Payment shows Chidinma Okafor", b"Chidinma Okafor" in resp.data)
check("Status=Awaiting Payment excludes Eze Ezekiel (paid)", b"Eze Ezekiel" not in resp.data)

# 7. No filters -> everything
resp = client.get("/admin/payments/search")
check("With no filters, both invoices are listed", b"Eze Ezekiel" in resp.data and b"Chidinma Okafor" in resp.data)

# 8. Paid row shows its receipt number
with app.app_context():
    db = get_db()
    receipt = db.execute(
        "SELECT receipt_number FROM receipt WHERE invoice_id = ?", (eze_invoice["invoice_id"],)
    ).fetchone()
resp = client.get("/admin/payments/search?status=Paid")
check("Paid invoice's row shows its receipt number", receipt["receipt_number"].encode() in resp.data)

client.get("/auth/logout")

# 9. Role separation
client.post("/auth/login", data={"role": "student", "login_id": "SUMAS/2022/0697", "password": "student123"})
resp = client.get("/admin/payments/search", follow_redirects=True)
check("Student session is refused the payment search route", b"only available to administrators" in resp.data)
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
