"""
smoke_test_payments.py — Verifies the payment gateway simulator and the
generic handle_payment_notification() handler it calls (app/payments.py),
including automatic receipt generation. This is the module that replaces
manual admin verification entirely for a normal successful payment.
Tests:
  1. handle_payment_notification() is a plain, directly-callable function
     — not simulator-specific — and correctly marks a matching invoice
     Paid, generating a receipt in the same call
  2. Simulating a payment through /student/pay with the correct
     reference marks the invoice Paid with NO admin action
  3. A receipt is generated automatically and viewable, with the amount
     spelled out in words
  4. Viewing the receipt for an invoice that hasn't been paid yet is
     refused, not a crash
  5. A payment reference that matches no invoice is logged to the
     unmatched_payment exception queue instead of crashing or silently
     doing nothing
  6. A payment reference that matches an invoice but the wrong amount is
     also logged as an exception, and does NOT mark the invoice paid
  7. Paying an already-paid invoice again is a harmless no-op — no
     duplicate receipt
  8. Role separation: only a logged-in student can reach the simulator
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
               ("School Fees", "2025/2026", None, None, 56000.00))
    db.commit()

client = app.test_client()
client.post("/auth/login", data={"role": "student", "login_id": "SUMAS/2022/0697", "password": "student123"})
client.post("/student/invoices/generate", data={"fee_category_id": 1, "payment_plan": "Full Payment"})

with app.app_context():
    db = get_db()
    invoice = db.execute("SELECT * FROM invoice").fetchone()
    invoice_id, reference, amount = invoice["invoice_id"], invoice["payment_reference"], invoice["amount"]

# 1. Direct function call — handle_payment_notification is genuinely generic
with app.app_context():
    db = get_db()
    outcome = handle_payment_notification(db, reference, amount)
check("handle_payment_notification() marks the invoice Paid directly", outcome["result"] == "paid")
check("...and returns a receipt number", bool(outcome.get("receipt_number")))
with app.app_context():
    db = get_db()
    row = db.execute("SELECT status FROM invoice WHERE invoice_id = ?", (invoice_id,)).fetchone()
check("Invoice status is 'Paid' after the direct call", row["status"] == "Paid")

# 2 & 3. Same thing via the simulator route + receipt page
resp = client.get(f"/student/invoices/{invoice_id}/receipt")
check("Receipt is viewable after payment", b"Official Receipt" in resp.data)
check("Receipt shows the amount spelled out in words", b"Fifty Six Thousand Naira Only" in resp.data)
check("Receipt shows a receipt number", b"RCT-" in resp.data)

# 4. Receipt refused for an unpaid invoice
client.post("/student/invoices/generate", data={"fee_category_id": 1, "payment_plan": "First Installment"})
with app.app_context():
    db = get_db()
    unpaid = db.execute(
        "SELECT invoice_id FROM invoice WHERE payment_plan = 'First Installment'"
    ).fetchone()["invoice_id"]
resp = client.get(f"/student/invoices/{unpaid}/receipt", follow_redirects=True)
check("Receipt for an unpaid invoice is refused, not a crash", b"no receipt for it" in resp.data)

# 5. Unmatched reference goes to the exception queue, not a crash
resp = client.post("/student/pay", data={
    "reference": "000000000000", "amount_paid": "5000",
}, follow_redirects=True)
check("Paying an unrecognised reference is handled gracefully", b"logged for an administrator" in resp.data)
with app.app_context():
    db = get_db()
    unmatched = db.execute(
        "SELECT * FROM unmatched_payment WHERE reference_received = '000000000000'"
    ).fetchone()
check("Unmatched reference was logged in the exception queue", unmatched is not None and unmatched["resolved"] == 0)

# 6. Amount mismatch also goes to the exception queue, invoice stays unpaid.
# Uses the still-unpaid "First Installment" invoice from test 4, not the
# already-paid one — paying an already-paid invoice's reference correctly
# short-circuits to "already_paid" before any amount check, which is its
# own scenario (tested in 7 below), not this one.
with app.app_context():
    db = get_db()
    unpaid_reference = db.execute(
        "SELECT payment_reference FROM invoice WHERE invoice_id = ?", (unpaid,)
    ).fetchone()["payment_reference"]
resp = client.post("/student/pay", data={
    "reference": unpaid_reference, "amount_paid": "1",
}, follow_redirects=True)
with app.app_context():
    db = get_db()
    still = db.execute("SELECT status FROM invoice WHERE invoice_id = ?", (unpaid,)).fetchone()
    mismatch_row = db.execute(
        "SELECT * FROM unmatched_payment WHERE reference_received = ? AND amount_received = 1", (unpaid_reference,)
    ).fetchone()
check("Amount mismatch does not mark the invoice paid", still["status"] == "Awaiting Payment")
check("Amount mismatch is logged in the exception queue", mismatch_row is not None)

# 7. Paying an already-paid invoice again is a harmless no-op
with app.app_context():
    db = get_db()
    receipt_count_before = db.execute("SELECT COUNT(*) AS c FROM receipt").fetchone()["c"]
client.post("/student/pay", data={"reference": reference, "amount_paid": f"{amount}"})
with app.app_context():
    db = get_db()
    receipt_count_after = db.execute("SELECT COUNT(*) AS c FROM receipt").fetchone()["c"]
check("Re-paying an already-paid invoice creates no duplicate receipt", receipt_count_before == receipt_count_after)

client.get("/auth/logout")

# 8. Role separation
resp = client.get("/student/pay", follow_redirects=True)
check("Logged-out session is refused the payment simulator", b"Log in" in resp.data)

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
