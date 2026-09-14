"""
admin.py — Administrator-facing routes.

This pass adds the Student & Fee Management module (Chapter 3, FRs):
  - "Add and manage student records."
  - "Create and manage fee structures (fee categories, amounts, and
     their applicable session, department, or faculty)."

The admin's role in the payment workflow has changed with the move to the
Invoice model (see PROJECT_BRIEF.md and DESIGN_BRIEF.md): a normal,
successful payment now needs NO admin action at all — it's matched and
receipted automatically by app/payments.py's handle_payment_notification().
Admin only sees payments in the **exception queue** below: notifications
that couldn't be matched to an invoice (wrong reference) or whose amount
didn't match what was owed. This replaces the old "verify every claim by
eye" workflow entirely.

This pass also adds Departmental Reporting: a payment-status roster,
filterable by department and level, for the admin to generate and send to
a Head of Department — the HOD never logs into the system themselves.

This pass also adds Search Payment Records: a lookup by student (reg
number or name) or payment reference, optionally narrowed by status —
the last item from the original functional-requirements list.
"""
import csv
import io
import sqlite3
from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for

from .auth import admin_required, hash_password
from .db import get_db
from .pdf import generate_departmental_report_pdf
from .payments import handle_payment_notification
from .student import _balance_rows

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/dashboard")
@admin_required
def dashboard():
    db = get_db()
    awaiting_count = db.execute(
        "SELECT COUNT(*) AS c FROM invoice WHERE status = 'Awaiting Payment'"
    ).fetchone()["c"]
    unresolved_count = db.execute(
        "SELECT COUNT(*) AS c FROM unmatched_payment WHERE resolved = 0"
    ).fetchone()["c"]
    student_count = db.execute("SELECT COUNT(*) AS c FROM student").fetchone()["c"]
    return render_template(
        "admin/dashboard.html",
        admin=g.user,
        awaiting_count=awaiting_count,
        unresolved_count=unresolved_count,
        student_count=student_count,
    )


# ---------------------------------------------------------------------------
# Student records
# ---------------------------------------------------------------------------

@bp.route("/students")
@admin_required
def list_students():
    db = get_db()
    q = request.args.get("q", "").strip()
    if q:
        students = db.execute(
            "SELECT * FROM student WHERE reg_number LIKE ? OR full_name LIKE ? "
            "ORDER BY full_name",
            (f"%{q}%", f"%{q}%"),
        ).fetchall()
    else:
        students = db.execute("SELECT * FROM student ORDER BY full_name").fetchall()
    return render_template("admin/students_list.html", students=students, q=q)


@bp.route("/students/add", methods=("GET", "POST"))
@admin_required
def add_student():
    if request.method == "POST":
        reg_number = request.form.get("reg_number", "").strip()
        full_name = request.form.get("full_name", "").strip()
        department = request.form.get("department", "").strip()
        faculty = request.form.get("faculty", "").strip()
        level = request.form.get("level", "").strip()
        password = request.form.get("password", "")

        error = None
        if not (reg_number and full_name and department and faculty and level and password):
            error = "All fields are required."

        if error is None:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO student (reg_number, full_name, department, faculty, level, password_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (reg_number, full_name, department, faculty, level, hash_password(password)),
                )
                db.commit()
                flash(f"Student {full_name} ({reg_number}) added successfully.", "success")
                return redirect(url_for("admin.list_students"))
            except sqlite3.IntegrityError:
                error = f"A student with registration number '{reg_number}' already exists."

        flash(error, "danger")

    return render_template("admin/student_form.html", student=None)


@bp.route("/students/<int:student_id>/edit", methods=("GET", "POST"))
@admin_required
def edit_student(student_id):
    db = get_db()
    student = db.execute(
        "SELECT * FROM student WHERE student_id = ?", (student_id,)
    ).fetchone()
    if student is None:
        flash("Student not found.", "danger")
        return redirect(url_for("admin.list_students"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        department = request.form.get("department", "").strip()
        faculty = request.form.get("faculty", "").strip()
        level = request.form.get("level", "").strip()
        new_password = request.form.get("password", "").strip()

        error = None
        if not (full_name and department and faculty and level):
            error = "Name, department, faculty, and level are required."

        if error is None:
            if new_password:
                db.execute(
                    "UPDATE student SET full_name=?, department=?, faculty=?, level=?, password_hash=? "
                    "WHERE student_id=?",
                    (full_name, department, faculty, level, hash_password(new_password), student_id),
                )
            else:
                db.execute(
                    "UPDATE student SET full_name=?, department=?, faculty=?, level=? WHERE student_id=?",
                    (full_name, department, faculty, level, student_id),
                )
            db.commit()
            flash("Student record updated.", "success")
            return redirect(url_for("admin.list_students"))

        flash(error, "danger")

    return render_template("admin/student_form.html", student=student)


# ---------------------------------------------------------------------------
# Fee categories / fee structures
# ---------------------------------------------------------------------------

def _normalise_fee_scope(category_name, department, faculty):
    """Enforces the FeeCategory scoping rule from Chapter 3, Section 3.4.3:
    School Fees -> both null; Departmental Fee -> department only;
    Faculty Fee -> faculty only. Returns (department, faculty, error)."""
    department = (department or "").strip()
    faculty = (faculty or "").strip()

    if category_name == "School Fees":
        return None, None, None
    elif category_name == "Departmental Fee":
        if not department:
            return None, None, "Department is required for a Departmental Fee."
        return department, None, None
    elif category_name == "Faculty Fee":
        if not faculty:
            return None, None, "Faculty is required for a Faculty Fee."
        return None, faculty, None
    else:
        return None, None, "Invalid fee category type."


@bp.route("/fees")
@admin_required
def list_fees():
    db = get_db()
    fees = db.execute(
        "SELECT * FROM fee_category ORDER BY session DESC, category_name, level, department, faculty"
    ).fetchall()
    return render_template("admin/fees_list.html", fees=fees)


@bp.route("/fees/add", methods=("GET", "POST"))
@admin_required
def add_fee():
    if request.method == "POST":
        category_name = request.form.get("category_name", "").strip()
        session = request.form.get("session", "").strip()
        # Optional for every category type (not just School Fees) — a blank
        # level means "applies to every level", the same NULL-is-a-wildcard
        # convention department/faculty already use for the other two types.
        level = request.form.get("level", "").strip() or None
        department_in = request.form.get("department", "").strip()
        faculty_in = request.form.get("faculty", "").strip()
        amount = request.form.get("amount", "").strip()

        error = None
        if not (category_name and session and amount):
            error = "Category, session, and amount are required."

        department, faculty, scope_error = _normalise_fee_scope(category_name, department_in, faculty_in)
        if error is None:
            error = scope_error

        if error is None:
            try:
                amount_val = float(amount)
                if amount_val <= 0:
                    error = "Amount must be greater than zero."
            except ValueError:
                error = "Amount must be a number."

        if error is None:
            db = get_db()
            # SQLite's UNIQUE constraint does not catch duplicates where
            # level/department/faculty are NULL (NULL is never equal to NULL
            # in SQL), so the same-scope check is also done explicitly here
            # using IS, which treats NULL = NULL as true.
            existing = db.execute(
                "SELECT 1 FROM fee_category WHERE category_name = ? AND session = ? "
                "AND level IS ? AND department IS ? AND faculty IS ?",
                (category_name, session, level, department, faculty),
            ).fetchone()
            if existing is not None:
                error = "A fee category with this exact category, session, level, department, and faculty already exists."

        if error is None:
            try:
                db.execute(
                    "INSERT INTO fee_category (category_name, session, level, department, faculty, amount) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (category_name, session, level, department, faculty, amount_val),
                )
                db.commit()
                flash(f"{category_name} for {session} added successfully.", "success")
                return redirect(url_for("admin.list_fees"))
            except sqlite3.IntegrityError:
                error = "A fee category with this exact category, session, level, department, and faculty already exists."

        flash(error, "danger")

    return render_template("admin/fee_form.html", fee=None)


@bp.route("/fees/<int:fee_category_id>/edit", methods=("GET", "POST"))
@admin_required
def edit_fee(fee_category_id):
    db = get_db()
    fee = db.execute(
        "SELECT * FROM fee_category WHERE fee_category_id = ?", (fee_category_id,)
    ).fetchone()
    if fee is None:
        flash("Fee category not found.", "danger")
        return redirect(url_for("admin.list_fees"))

    if request.method == "POST":
        amount = request.form.get("amount", "").strip()
        error = None
        try:
            amount_val = float(amount)
            if amount_val <= 0:
                error = "Amount must be greater than zero."
        except ValueError:
            error = "Amount must be a number."

        if error is None:
            db.execute(
                "UPDATE fee_category SET amount = ? WHERE fee_category_id = ?",
                (amount_val, fee_category_id),
            )
            db.commit()
            flash("Fee amount updated.", "success")
            return redirect(url_for("admin.list_fees"))

        flash(error, "danger")

    return render_template("admin/fee_form.html", fee=fee)


# ---------------------------------------------------------------------------
# Department programme lengths — how far each department's own course
# actually runs (most run to 400 Level; some, like Nursing Science, run
# longer). A department with no row here defaults to 400 in code (see
# `_max_level_for()` in app/student.py) — this list only ever needs an
# entry for a department whose programme is NOT that common 400L case.
# Drives the Level select's range on the student invoice-generation form.
# ---------------------------------------------------------------------------

LEVEL_CHOICES = ("400", "500", "600")


@bp.route("/programs")
@admin_required
def list_programs():
    db = get_db()
    programs = db.execute(
        "SELECT * FROM department_program ORDER BY department"
    ).fetchall()
    return render_template("admin/programs_list.html", programs=programs)


@bp.route("/programs/add", methods=("GET", "POST"))
@admin_required
def add_program():
    if request.method == "POST":
        department = request.form.get("department", "").strip()
        max_level = request.form.get("max_level", "").strip()

        error = None
        if not (department and max_level):
            error = "Department and maximum level are both required."
        if error is None and max_level not in LEVEL_CHOICES:
            error = "Invalid maximum level."

        if error is None:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO department_program (department, max_level) VALUES (?, ?)",
                    (department, max_level),
                )
                db.commit()
                flash(f"{department} set to run through {max_level} Level.", "success")
                return redirect(url_for("admin.list_programs"))
            except sqlite3.IntegrityError:
                error = f"{department} already has a programme length set — edit it instead."

        flash(error, "danger")

    return render_template("admin/program_form.html", program=None, level_choices=LEVEL_CHOICES)


@bp.route("/programs/<department>/edit", methods=("GET", "POST"))
@admin_required
def edit_program(department):
    db = get_db()
    program = db.execute(
        "SELECT * FROM department_program WHERE department = ?", (department,)
    ).fetchone()
    if program is None:
        flash("That department has no programme length set yet.", "danger")
        return redirect(url_for("admin.list_programs"))

    if request.method == "POST":
        max_level = request.form.get("max_level", "").strip()
        error = None
        if max_level not in LEVEL_CHOICES:
            error = "Invalid maximum level."

        if error is None:
            db.execute(
                "UPDATE department_program SET max_level = ? WHERE department = ?",
                (max_level, department),
            )
            db.commit()
            flash("Programme length updated.", "success")
            return redirect(url_for("admin.list_programs"))

        flash(error, "danger")

    return render_template("admin/program_form.html", program=program, level_choices=LEVEL_CHOICES)


@bp.route("/programs/<department>/delete", methods=("POST",))
@admin_required
def delete_program(department):
    db = get_db()
    db.execute("DELETE FROM department_program WHERE department = ?", (department,))
    db.commit()
    flash(f"{department} now defaults back to 400 Level.", "success")
    return redirect(url_for("admin.list_programs"))


# ---------------------------------------------------------------------------
# Exception queue — payment notifications that couldn't be automatically
# matched to an invoice. This is the ONLY payment-related admin screen
# now; a normal successful payment never appears here at all.
# ---------------------------------------------------------------------------

@bp.route("/unmatched")
@admin_required
def list_unmatched():
    db = get_db()
    unmatched = db.execute(
        "SELECT * FROM unmatched_payment WHERE resolved = 0 ORDER BY date_received"
    ).fetchall()
    return render_template("admin/unmatched_list.html", unmatched=unmatched)


def _unresolved_or_none(db, unmatched_id):
    return db.execute(
        "SELECT * FROM unmatched_payment WHERE unmatched_id = ? AND resolved = 0",
        (unmatched_id,),
    ).fetchone()


@bp.route("/unmatched/<int:unmatched_id>/match", methods=("POST",))
@admin_required
def match_unmatched(unmatched_id):
    db = get_db()
    row = _unresolved_or_none(db, unmatched_id)
    if row is None:
        flash("That exception was not found (it may already be resolved).", "danger")
        return redirect(url_for("admin.list_unmatched"))

    correct_reference = request.form.get("correct_reference", "").strip()
    if not correct_reference:
        flash("Enter the correct payment reference to match this payment to.", "danger")
        return redirect(url_for("admin.list_unmatched"))

    # Re-run the SAME matching logic a real gateway notification would go
    # through — resolving an exception is just "try again with the
    # reference the student actually meant to quote."
    outcome = handle_payment_notification(db, correct_reference, row["amount_received"])

    if outcome["result"] == "paid":
        db.execute(
            "UPDATE unmatched_payment SET resolved = 1, resolved_by = ?, "
            "date_resolved = datetime('now') WHERE unmatched_id = ?",
            (g.user["admin_id"], unmatched_id),
        )
        db.commit()
        flash(f"Matched to invoice — receipt {outcome['receipt_number']} generated.", "success")
    elif outcome["result"] == "already_paid":
        flash("That invoice was already marked as paid — nothing changed here.", "danger")
    elif outcome["result"] == "amount_mismatch":
        flash(
            f"That reference matched an invoice, but for ₦{outcome['invoice']['amount']:,.2f}, "
            f"not the ₦{row['amount_received']:,.2f} received. Still unresolved.",
            "danger",
        )
    else:
        flash("That reference didn't match any invoice either. Still unresolved.", "danger")

    return redirect(url_for("admin.list_unmatched"))


@bp.route("/unmatched/<int:unmatched_id>/dismiss", methods=("POST",))
@admin_required
def dismiss_unmatched(unmatched_id):
    db = get_db()
    row = _unresolved_or_none(db, unmatched_id)
    if row is None:
        flash("That exception was not found (it may already be resolved).", "danger")
        return redirect(url_for("admin.list_unmatched"))

    db.execute(
        "UPDATE unmatched_payment SET resolved = 1, resolved_by = ?, "
        "date_resolved = datetime('now') WHERE unmatched_id = ?",
        (g.user["admin_id"], unmatched_id),
    )
    db.commit()
    flash("Dismissed.", "success")
    return redirect(url_for("admin.list_unmatched"))


# ---------------------------------------------------------------------------
# Departmental Reporting — a payment-status roster the admin generates and
# sends to a Head of Department. The HOD never logs into the system; there
# is no HOD-facing view anywhere in this app, only this admin-generated
# report (print/PDF via the browser, or a CSV download to attach to an
# email — see _departmental_report_rows(), shared by both).
# ---------------------------------------------------------------------------

def _departmental_report_rows(db, department, level):
    """One row per student matching the (optional) department/level
    filters, with the SAME balance figures the student's own Outstanding
    Balance page shows — reuses student.py's _balance_rows() rather than
    recomputing the fee-scoping/payment logic a third time."""
    query = "SELECT * FROM student WHERE 1=1"
    params = []
    if department:
        query += " AND department = ?"
        params.append(department)
    if level:
        query += " AND level = ?"
        params.append(level)
    query += " ORDER BY full_name"
    students = db.execute(query, params).fetchall()

    rows = []
    for s in students:
        balances = _balance_rows(db, s)
        total_owed = sum(b["amount_owed"] for b in balances)
        total_paid = sum(b["amount_paid"] for b in balances)
        rows.append({
            "reg_number": s["reg_number"],
            "full_name": s["full_name"],
            "department": s["department"],
            "faculty": s["faculty"],
            "level": s["level"],
            "total_owed": total_owed,
            "total_paid": total_paid,
            "balance": total_owed - total_paid,
        })
    return rows


@bp.route("/reports/departmental")
@admin_required
def departmental_report():
    db = get_db()
    department = request.args.get("department", "").strip()
    level = request.args.get("level", "").strip()

    departments = [r["department"] for r in db.execute("SELECT DISTINCT department FROM student ORDER BY department")]
    levels = [r["level"] for r in db.execute("SELECT DISTINCT level FROM student ORDER BY level")]
    rows = _departmental_report_rows(db, department, level)

    return render_template(
        "admin/departmental_report.html",
        rows=rows,
        departments=departments,
        levels=levels,
        department=department,
        level=level,
    )


@bp.route("/reports/departmental/export")
@admin_required
def departmental_report_export():
    db = get_db()
    department = request.args.get("department", "").strip()
    level = request.args.get("level", "").strip()
    rows = _departmental_report_rows(db, department, level)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Reg. Number", "Full Name", "Department", "Faculty", "Level",
        "Total Owed", "Total Paid", "Balance", "Status",
    ])
    for r in rows:
        writer.writerow([
            r["reg_number"], r["full_name"], r["department"], r["faculty"], r["level"],
            f"{r['total_owed']:.2f}", f"{r['total_paid']:.2f}", f"{r['balance']:.2f}",
            "Fully Paid" if r["balance"] <= 0 else "Outstanding",
        ])

    filename = f"payment-status-report-{department or 'all-departments'}-{level or 'all-levels'}.csv"
    filename = filename.replace(" ", "-")
    response = Response(buffer.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=\"{filename}\""
    return response


@bp.route("/reports/departmental/pdf")
@admin_required
def departmental_report_pdf():
    db = get_db()
    department = request.args.get("department", "").strip()
    level = request.args.get("level", "").strip()
    rows = _departmental_report_rows(db, department, level)
    pdf = generate_departmental_report_pdf(rows, department, level)

    filename = f"payment-status-report-{department or 'all-departments'}-{level or 'all-levels'}.pdf"
    filename = filename.replace(" ", "-")
    response = Response(pdf.read(), mimetype="application/pdf")
    response.headers["Content-Disposition"] = f"attachment; filename=\"{filename}\""
    return response


# ---------------------------------------------------------------------------
# Search Payment Records — the last item from the original functional-
# requirements list (Chapter 3, Section 3.1.1). Every invoice IS a payment
# record under this model (an "Awaiting Payment" one is a pending payment,
# a "Paid" one is a completed one with its receipt), so this searches the
# invoice table directly — by student (reg number or name) or by payment
# reference, optionally narrowed by status. It's a lookup tool, not a
# report to hand out, so unlike Departmental Reporting it has no CSV/print.
# ---------------------------------------------------------------------------

def _payment_search_rows(db, q, status):
    query = (
        "SELECT invoice.*, student.reg_number, student.full_name, "
        "       fee_category.category_name, fee_category.session, fee_category.level, "
        "       receipt.receipt_number "
        "FROM invoice "
        "JOIN student ON invoice.student_id = student.student_id "
        "JOIN fee_category ON invoice.fee_category_id = fee_category.fee_category_id "
        "LEFT JOIN receipt ON receipt.invoice_id = invoice.invoice_id "
        "WHERE 1=1"
    )
    params = []
    if q:
        query += (
            " AND (student.reg_number LIKE ? OR student.full_name LIKE ? "
            "OR invoice.payment_reference LIKE ?)"
        )
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if status in ("Awaiting Payment", "Paid"):
        query += " AND invoice.status = ?"
        params.append(status)
    query += " ORDER BY invoice.date_generated DESC"
    return db.execute(query, params).fetchall()


@bp.route("/payments/search")
@admin_required
def search_payments():
    db = get_db()
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    rows = _payment_search_rows(db, q, status)
    return render_template("admin/payment_search.html", rows=rows, q=q, status=status)
