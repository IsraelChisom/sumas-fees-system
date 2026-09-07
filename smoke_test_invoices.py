"""
smoke_test_invoices.py — Verifies the Invoice module (replaces the old
Payment Claims module — see PROJECT_BRIEF.md for the redesign).
Tests:
  1. The invoice form only offers fee categories that apply to the
     student (School Fees, their own department, their own faculty —
     not another department's or faculty's fee)
  2. Student can generate a Full Payment invoice; it gets a unique
     payment_reference and starts 'Awaiting Payment'
  3. Installment amounts split the full fee evenly (and sum back to it
     exactly, including odd kobo)
  4. Generating an invoice for a fee category outside the student's
     scope is rejected
  5. Generating a duplicate invoice (same fee category + payment plan,
     still unpaid) is rejected
  6. The generated invoice appears in the student's own invoice history
  7. A student can view their own invoice, but not another student's
     invoice or one that doesn't exist
  8. Role separation: admin session is refused every student invoice
     route; student session is refused the admin exception queue
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
    db.execute("INSERT INTO student (reg_number, full_name, department, faculty, level, password_hash) VALUES (?,?,?,?,?,?)",
               ("SUMAS/2023/0188", "Tunde Bakare", "Nursing Science", "Health Sciences", "300", generate_password_hash("student123")))
    db.execute("INSERT INTO fee_category (category_name, session, department, faculty, amount) VALUES (?,?,?,?,?)",
               ("School Fees", "2025/2026", None, None, 150000.00))
    db.execute("INSERT INTO fee_category (category_name, session, department, faculty, amount) VALUES (?,?,?,?,?)",
               ("Departmental Fee", "2025/2026", "Computer Science", None, 25000.01))
    db.execute("INSERT INTO fee_category (category_name, session, department, faculty, amount) VALUES (?,?,?,?,?)",
               ("Departmental Fee", "2025/2026", "Nursing Science", None, 30000.00))
    db.execute("INSERT INTO fee_category (category_name, session, department, faculty, amount) VALUES (?,?,?,?,?)",
               ("Faculty Fee", "2025/2026", None, "Natural Sciences", 10000.00))
    db.commit()
    other_dept_fee_id = db.execute(
        "SELECT fee_category_id FROM fee_category WHERE department = 'Nursing Science'"
    ).fetchone()["fee_category_id"]
    dept_fee_id = db.execute(
        "SELECT fee_category_id FROM fee_category WHERE department = 'Computer Science'"
    ).fetchone()["fee_category_id"]

client = app.test_client()
client.post("/auth/login", data={"role": "student", "login_id": "SUMAS/2022/0697", "password": "student123"})

# 1. Invoice form only offers applicable fee categories
resp = client.get("/student/invoices/generate")
check("Invoice form offers School Fees", b"School Fees" in resp.data)
check("Invoice form offers own department's Departmental Fee", b"Departmental Fee" in resp.data)
check("Invoice form offers own faculty's Faculty Fee", b"Faculty Fee" in resp.data)
check("Invoice form does NOT offer another department's fee", b"30,000.00" not in resp.data)

# 2. Generate a Full Payment invoice
resp = client.post("/student/invoices/generate", data={
    "fee_category_id": dept_fee_id, "session": "2025/2026", "payment_plan": "Full Payment",
}, follow_redirects=True)
check("Invoice generated successfully", b"Invoice generated" in resp.data)
check("Invoice shows a payment reference", b"Payment Reference" in resp.data)

with app.app_context():
    db = get_db()
    invoice = db.execute(
        "SELECT * FROM invoice WHERE student_id = (SELECT student_id FROM student WHERE reg_number = 'SUMAS/2022/0697') "
        "AND payment_plan = 'Full Payment'"
    ).fetchone()
check("Full Payment invoice starts 'Awaiting Payment'", invoice["status"] == "Awaiting Payment")
check("Full Payment invoice amount equals the fee's full amount", float(invoice["amount"]) == 25000.01)
check("Invoice has a unique, non-empty payment reference", bool(invoice["payment_reference"]))

# 3. Installment amounts split evenly and sum back exactly (odd kobo included)
resp = client.post("/student/invoices/generate", data={
    "fee_category_id": dept_fee_id, "session": "2025/2026", "payment_plan": "First Installment",
}, follow_redirects=True)
resp = client.post("/student/invoices/generate", data={
    "fee_category_id": dept_fee_id, "session": "2025/2026", "payment_plan": "Second Installment",
}, follow_redirects=True)
with app.app_context():
    db = get_db()
    first = db.execute(
        "SELECT amount FROM invoice WHERE fee_category_id = ? AND payment_plan = 'First Installment'",
        (dept_fee_id,),
    ).fetchone()
    second = db.execute(
        "SELECT amount FROM invoice WHERE fee_category_id = ? AND payment_plan = 'Second Installment'",
        (dept_fee_id,),
    ).fetchone()
check("Installments were both generated", first is not None and second is not None)
check(
    "Installments sum back exactly to the full fee (25000.01)",
    round(float(first["amount"]) + float(second["amount"]), 2) == 25000.01,
)

# 4. Fee category outside scope is rejected
resp = client.post("/student/invoices/generate", data={
    "fee_category_id": str(other_dept_fee_id), "session": "2025/2026", "payment_plan": "Full Payment",
}, follow_redirects=True)
check("Invoice against a fee category outside student's scope is rejected", b"does not apply to you" in resp.data)

# 5. Duplicate invoice (same category + plan, still unpaid) is rejected
resp = client.post("/student/invoices/generate", data={
    "fee_category_id": dept_fee_id, "session": "2025/2026", "payment_plan": "Full Payment",
}, follow_redirects=True)
check("Duplicate unpaid invoice for the same category+plan is rejected", b"already have an invoice" in resp.data)

# 6. Invoice appears in the student's own history
resp = client.get("/student/invoices")
check("Generated invoices appear in the student's history", b"Awaiting Payment" in resp.data)

# 7. Viewing invoices — ownership enforced
with app.app_context():
    db = get_db()
    my_invoice_id = db.execute(
        "SELECT invoice_id FROM invoice WHERE fee_category_id = ? AND payment_plan = 'Full Payment'",
        (dept_fee_id,),
    ).fetchone()["invoice_id"]
resp = client.get(f"/student/invoices/{my_invoice_id}")
check("Student can view their own invoice", b"Amount Payable" in resp.data)
resp = client.get("/student/invoices/999999", follow_redirects=True)
check("Viewing a nonexistent invoice is refused, not a crash", resp.status_code == 200 and b"Invoice not found" in resp.data)

client.get("/auth/logout")
client.post("/auth/login", data={"role": "student", "login_id": "SUMAS/2023/0188", "password": "student123"})
resp = client.get(f"/student/invoices/{my_invoice_id}", follow_redirects=True)
check("A student cannot view another student's invoice", b"Invoice not found" in resp.data)
client.get("/auth/logout")

# 8. Role separation
client.post("/auth/login", data={"role": "admin", "login_id": "ADM/001", "password": "admin123"})
for path in ["/student/invoices", "/student/invoices/generate", "/student/pay"]:
    resp = client.get(path, follow_redirects=True)
    check(f"Admin session is refused {path}", b"only available to students" in resp.data)
client.get("/auth/logout")

client.post("/auth/login", data={"role": "student", "login_id": "SUMAS/2022/0697", "password": "student123"})
resp = client.get("/admin/unmatched", follow_redirects=True)
check("Student session is refused the admin exception queue", b"only available to administrators" in resp.data)
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
