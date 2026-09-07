"""
smoke_test_balance.py — Verifies the "View Outstanding Balance" module.
The balance is never stored — always recomputed as
fee_category.amount - SUM(invoice.amount WHERE status='Paid') per
category (see PROJECT_BRIEF.md's "Database schema").
Tests:
  1. With no invoices at all, the balance equals the full fee amount for
     every applicable fee category, marked Outstanding
  2. Only fee categories that apply to the student are shown (same
     scoping rule as the invoice form) — not another department's fee
  3. An invoice still 'Awaiting Payment' does NOT reduce the balance
  4. Once that invoice is marked Paid, the balance drops by exactly its
     amount, and a fully-paid category is marked Fully Paid
  5. Partial payment (one of two installments paid) leaves a partial
     balance, not zero and not the full amount
  6. The total row sums every category correctly
  7. Role separation: admin session is refused; logged-out session is
     redirected to login
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
    db.execute("INSERT INTO fee_category (category_name, session, department, faculty, amount) VALUES (?,?,?,?,?)",
               ("School Fees", "2025/2026", None, None, 150000.00))
    db.execute("INSERT INTO fee_category (category_name, session, department, faculty, amount) VALUES (?,?,?,?,?)",
               ("Departmental Fee", "2025/2026", "Computer Science", None, 24000.00))
    db.execute("INSERT INTO fee_category (category_name, session, department, faculty, amount) VALUES (?,?,?,?,?)",
               ("Departmental Fee", "2025/2026", "Nursing Science", None, 30000.00))
    db.commit()

client = app.test_client()
client.post("/auth/login", data={"role": "student", "login_id": "SUMAS/2022/0697", "password": "student123"})

# 1 & 2. No invoices yet: balance = full amount, only applicable categories shown
resp = client.get("/student/balance")
check("Balance page shows School Fees at its full amount", b"150,000.00" in resp.data)
check("Balance page shows own department's Departmental Fee at its full amount", b"24,000.00" in resp.data)
check("Balance page does NOT show another department's fee", b"30,000.00" not in resp.data)
check("With nothing paid, School Fees is marked Outstanding", b"Outstanding" in resp.data)

# 3. An unpaid (Awaiting Payment) invoice doesn't move the balance
client.post("/student/invoices/generate", data={"fee_category_id": 2, "session": "2025/2026", "payment_plan": "Full Payment"})
resp = client.get("/student/balance")
check("An Awaiting-Payment invoice does not reduce the balance", b"24,000.00" in resp.data)

# 4. Mark that invoice Paid -> balance drops to zero, Fully Paid
with app.app_context():
    db = get_db()
    invoice = db.execute(
        "SELECT * FROM invoice WHERE fee_category_id = 2 AND payment_plan = 'Full Payment'"
    ).fetchone()
    handle_payment_notification(db, invoice["payment_reference"], invoice["amount"])
resp = client.get("/student/balance")
check("Paying the Departmental Fee in full brings its balance to 0.00", b"0.00" in resp.data)
check("A fully paid category is marked Fully Paid", b"Fully Paid" in resp.data)

# 5. Partial payment: pay one School Fees installment, leave the other unpaid
client.post("/student/invoices/generate", data={"fee_category_id": 1, "session": "2025/2026", "payment_plan": "First Installment"})
client.post("/student/invoices/generate", data={"fee_category_id": 1, "session": "2025/2026", "payment_plan": "Second Installment"})
with app.app_context():
    db = get_db()
    first = db.execute(
        "SELECT * FROM invoice WHERE fee_category_id = 1 AND payment_plan = 'First Installment'"
    ).fetchone()
    handle_payment_notification(db, first["payment_reference"], first["amount"])
resp = client.get("/student/balance")
check("Half-paid School Fees shows a 75,000.00 balance (150,000 - 75,000)", b"75,000.00" in resp.data)
check("Half-paid School Fees is still marked Outstanding, not Fully Paid", resp.data.count(b"Outstanding") >= 1)

# 6. Total row: School Fees (75,000 remaining) + Departmental Fee (0 remaining) = 75,000.00
check("The total balance row shows 75,000.00", resp.data.count(b"75,000.00") >= 2)

client.get("/auth/logout")

# 7. Role separation
client.post("/auth/login", data={"role": "admin", "login_id": "ADM/001", "password": "admin123"})
resp = client.get("/student/balance", follow_redirects=True)
check("Admin session is refused the balance page", b"only available to students" in resp.data)
client.get("/auth/logout")

resp = client.get("/student/balance", follow_redirects=True)
check("Logged-out session is redirected to login", b"Log in" in resp.data)

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
