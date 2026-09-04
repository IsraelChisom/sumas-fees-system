"""
smoke_test_exceptions.py — Verifies the admin exception queue
(unmatched payments), the only payment-related screen an admin still
uses under the new Invoice workflow.
Tests:
  1. Admin sees an unmatched payment notification in the queue
  2. Admin can "Match" it to the correct invoice reference — this re-runs
     the SAME handle_payment_notification() the simulator uses, marking
     the invoice Paid, generating a receipt, and resolving the row
  3. Matching to a reference that's still wrong leaves the row unresolved
     with a clear message (not silently dropped)
  4. Admin can "Dismiss" a row without matching it, and it disappears
     from the unresolved queue
  5. Acting on an already-resolved (or nonexistent) row is refused
     gracefully, not a crash
  6. Role separation: a student session is refused every exception-queue
     route
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
               ("SUMAS/2022/0697", "Eze Ezekiel", "Computer Science", "Natural Sciences", "400", generate_password_hash("student123")))
    db.execute("INSERT INTO fee_category (category_name, session, department, faculty, amount) VALUES (?,?,?,?,?)",
               ("School Fees", "2025/2026", None, None, 56000.00))
    db.commit()

client = app.test_client()

# Student generates an invoice, then "pays" using the WRONG reference —
# this is what lands the payment in the exception queue.
client.post("/auth/login", data={"role": "student", "login_id": "SUMAS/2022/0697", "password": "student123"})
client.post("/student/invoices/generate", data={"fee_category_id": 1, "payment_plan": "Full Payment"})
with app.app_context():
    db = get_db()
    invoice = db.execute("SELECT * FROM invoice").fetchone()
    invoice_id, correct_reference, amount = invoice["invoice_id"], invoice["payment_reference"], invoice["amount"]
client.post("/student/pay", data={"reference": "999999999999", "amount_paid": f"{amount}"})
client.get("/auth/logout")

client.post("/auth/login", data={"role": "admin", "login_id": "ADM/001", "password": "admin123"})

# 1. Queue shows it
resp = client.get("/admin/unmatched")
check("Admin sees the unmatched payment in the queue", b"999999999999" in resp.data)

with app.app_context():
    db = get_db()
    unmatched = db.execute(
        "SELECT unmatched_id FROM unmatched_payment WHERE reference_received = '999999999999'"
    ).fetchone()
    unmatched_id = unmatched["unmatched_id"]

# 3. Matching with a still-wrong reference leaves it unresolved
resp = client.post(f"/admin/unmatched/{unmatched_id}/match", data={
    "correct_reference": "111111111111",
}, follow_redirects=True)
check("Matching to another wrong reference is refused with a clear message", b"Still unresolved" in resp.data)
with app.app_context():
    db = get_db()
    still_unresolved = db.execute(
        "SELECT resolved FROM unmatched_payment WHERE unmatched_id = ?", (unmatched_id,)
    ).fetchone()
check("Row is still unresolved after a failed match attempt", still_unresolved["resolved"] == 0)

# 2. Matching with the CORRECT reference resolves it and pays the invoice
resp = client.post(f"/admin/unmatched/{unmatched_id}/match", data={
    "correct_reference": correct_reference,
}, follow_redirects=True)
check("Matching to the correct reference succeeds", b"receipt" in resp.data and b"generated" in resp.data)
with app.app_context():
    db = get_db()
    resolved_row = db.execute(
        "SELECT * FROM unmatched_payment WHERE unmatched_id = ?", (unmatched_id,)
    ).fetchone()
    paid_invoice = db.execute("SELECT status FROM invoice WHERE invoice_id = ?", (invoice_id,)).fetchone()
    receipt = db.execute("SELECT * FROM receipt WHERE invoice_id = ?", (invoice_id,)).fetchone()
check("Exception row is marked resolved, with resolved_by recorded", resolved_row["resolved"] == 1 and resolved_row["resolved_by"] is not None)
check("The invoice is now Paid", paid_invoice["status"] == "Paid")
check("A receipt was generated for it", receipt is not None)

resp = client.get("/admin/unmatched")
check("Resolved row no longer appears in the unresolved queue", b"999999999999" not in resp.data)

# 5. Acting on an already-resolved row is refused gracefully
resp = client.post(f"/admin/unmatched/{unmatched_id}/dismiss", follow_redirects=True)
check("Dismissing an already-resolved row is refused, not a crash", b"was not found" in resp.data)
resp = client.post("/admin/unmatched/999999/match", data={"correct_reference": "x"}, follow_redirects=True)
check("Matching a nonexistent exception is refused, not a crash", resp.status_code == 200 and b"was not found" in resp.data)

# 4. Dismiss without matching
with app.app_context():
    db = get_db()
    db.execute(
        "INSERT INTO unmatched_payment (reference_received, amount_received) VALUES (?, ?)",
        ("222222222222", 1000),
    )
    db.commit()
    dismiss_id = db.execute(
        "SELECT unmatched_id FROM unmatched_payment WHERE reference_received = '222222222222'"
    ).fetchone()["unmatched_id"]
resp = client.post(f"/admin/unmatched/{dismiss_id}/dismiss", follow_redirects=True)
check("Dismiss succeeds", b"Dismissed" in resp.data)
resp = client.get("/admin/unmatched")
check("Dismissed row no longer appears in the queue", b"222222222222" not in resp.data)

client.get("/auth/logout")

# 6. Role separation
client.post("/auth/login", data={"role": "student", "login_id": "SUMAS/2022/0697", "password": "student123"})
resp = client.get("/admin/unmatched", follow_redirects=True)
check("Student session is refused the exception queue list", b"only available to administrators" in resp.data)
resp = client.post(f"/admin/unmatched/{dismiss_id}/dismiss", follow_redirects=True)
check("Student session is refused the dismiss route", b"only available to administrators" in resp.data)
resp = client.post(f"/admin/unmatched/{dismiss_id}/match", data={"correct_reference": "x"}, follow_redirects=True)
check("Student session is refused the match route", b"only available to administrators" in resp.data)
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
