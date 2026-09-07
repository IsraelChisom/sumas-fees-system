"""
student.py — Student-facing routes.

This pass replaces the earlier "submit a claim, admin verifies it by eye"
Payment Claims module with the Invoice workflow (see PROJECT_BRIEF.md and
DESIGN_BRIEF.md for the full rationale — this mirrors a real system used
at the University of Nigeria, Nsukka):

  1. Student picks a fee category + payment plan and generates an Invoice
     carrying a unique payment reference (generate_invoice()).
  2. Student pays that reference externally. Since there's no real payment
     gateway available for this project, that step is simulated
     (pay_simulator()) — but the simulator calls the exact same
     `handle_payment_notification()` (app/payments.py) that a real
     gateway's webhook would call, so the matching logic itself is not a
     simulation of anything.
  3. A successful match marks the invoice Paid and generates a Receipt
     automatically — no admin action. The student can view/print both
     anytime from their invoice history (list_invoices()).
"""
import sqlite3

from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for

from .auth import student_required
from .db import get_db
from .pdf import generate_invoice_pdf, generate_receipt_pdf
from .payments import (
    amount_in_words,
    generate_payment_reference,
    invoice_amount_for_plan,
    handle_payment_notification,
)

bp = Blueprint("student", __name__, url_prefix="/student")

PAYMENT_PLANS = ("Full Payment", "First Installment", "Second Installment")


@bp.route("/dashboard")
@student_required
def dashboard():
    db = get_db()
    invoice_counts = db.execute(
        "SELECT "
        "  SUM(CASE WHEN status = 'Awaiting Payment' THEN 1 ELSE 0 END) AS awaiting, "
        "  SUM(CASE WHEN status = 'Paid' THEN 1 ELSE 0 END) AS paid "
        "FROM invoice WHERE student_id = ?",
        (g.user["student_id"],),
    ).fetchone()
    balance_rows = _balance_rows(db, g.user)
    total_owed = sum(row["amount_owed"] for row in balance_rows)
    total_paid = sum(row["amount_paid"] for row in balance_rows)
    return render_template(
        "student/dashboard.html",
        student=g.user,
        invoices_awaiting=invoice_counts["awaiting"] or 0,
        invoices_paid=invoice_counts["paid"] or 0,
        balance_rows=balance_rows,
        total_owed=total_owed,
        total_paid=total_paid,
        total_balance=total_owed - total_paid,
    )


# ---------------------------------------------------------------------------
# Fee category scoping (shared with the invoice-generation form)
# ---------------------------------------------------------------------------

def _applicable_fee_categories(db, student):
    """Given a student, finds the fee_category rows that apply to them right
    now: every School Fees row, plus Departmental Fee rows for their own
    department, plus Faculty Fee rows for their own faculty — narrowed to
    rows whose `level` is either NULL ("all levels") or matches the
    student's own registered level. Mirrors `_normalise_fee_scope` in
    admin.py in reverse (same scoping rule from Chapter 3, Section 3.4.3,
    read the other way round). Used for the student's outstanding balance
    and the admin's departmental report — both describe what a student
    owes *at their current level*, not every level a fee category exists
    for (that wider set is `_fee_categories_for_invoice_form()` below)."""
    return db.execute(
        "SELECT * FROM fee_category "
        "WHERE (level IS NULL OR level = ?) "
        "  AND (category_name = 'School Fees' "
        "   OR (category_name = 'Departmental Fee' AND department = ?) "
        "   OR (category_name = 'Faculty Fee' AND faculty = ?)) "
        "ORDER BY session DESC, category_name",
        (student["level"], student["department"], student["faculty"]),
    ).fetchall()


def _fee_categories_for_invoice_form(db, student):
    """The wider set used only by the invoice-generation form: every fee
    category scoped to the student's department/faculty as above, but
    across *every* level and session, not just the student's current one —
    a student who needs to settle a fee for a level or session other than
    their present one (e.g. a carried-over balance) can still select it.
    The form itself narrows this list to one level/session at a time via
    the Level/Session selects (see invoice_generate.html); the fee
    category actually chosen is re-validated against this same list on
    POST, so nothing here has to be trusted from the client."""
    return db.execute(
        "SELECT * FROM fee_category "
        "WHERE category_name = 'School Fees' "
        "   OR (category_name = 'Departmental Fee' AND department = ?) "
        "   OR (category_name = 'Faculty Fee' AND faculty = ?) "
        "ORDER BY session DESC, level, category_name",
        (student["department"], student["faculty"]),
    ).fetchall()


# ---------------------------------------------------------------------------
# Outstanding balance — never stored, always recomputed (same principle as
# the invoice/receipt model: see PROJECT_BRIEF.md's "Database schema").
# Shared by the dashboard (just the total) and the full balance page.
# ---------------------------------------------------------------------------

def _balance_rows(db, student):
    """One row per fee category applicable to `student`: what's owed, what's
    been paid (confirmed invoices only), and the balance."""
    rows = []
    for fc in _applicable_fee_categories(db, student):
        paid = db.execute(
            "SELECT COALESCE(SUM(amount), 0) AS paid FROM invoice "
            "WHERE student_id = ? AND fee_category_id = ? AND status = 'Paid'",
            (student["student_id"], fc["fee_category_id"]),
        ).fetchone()["paid"]
        owed = float(fc["amount"])
        paid = float(paid)
        rows.append({
            "category_name": fc["category_name"],
            "session": fc["session"],
            "amount_owed": owed,
            "amount_paid": paid,
            "balance": owed - paid,
        })
    return rows


@bp.route("/balance")
@student_required
def view_balance():
    db = get_db()
    rows = _balance_rows(db, g.user)
    total_owed = sum(row["amount_owed"] for row in rows)
    total_paid = sum(row["amount_paid"] for row in rows)
    return render_template(
        "student/balance.html",
        rows=rows,
        total_owed=total_owed,
        total_paid=total_paid,
        total_balance=total_owed - total_paid,
    )


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------

@bp.route("/invoices")
@student_required
def list_invoices():
    db = get_db()
    invoices = db.execute(
        "SELECT invoice.*, fee_category.category_name, fee_category.session, "
        "       fee_category.level, receipt.receipt_number "
        "FROM invoice "
        "JOIN fee_category ON invoice.fee_category_id = fee_category.fee_category_id "
        "LEFT JOIN receipt ON receipt.invoice_id = invoice.invoice_id "
        "WHERE invoice.student_id = ? "
        "ORDER BY invoice.date_generated DESC",
        (g.user["student_id"],),
    ).fetchall()
    return render_template("student/invoices_list.html", invoices=invoices)


@bp.route("/invoices/generate", methods=("GET", "POST"))
@student_required
def generate_invoice():
    db = get_db()
    fee_categories = _fee_categories_for_invoice_form(db, g.user)
    levels = sorted({f["level"] for f in fee_categories if f["level"]})
    sessions = sorted({f["session"] for f in fee_categories}, reverse=True)

    if request.method == "POST":
        # Security NFR: which student an invoice belongs to is always
        # taken from the logged-in session (g.user), never from the form.
        fee_category_id = request.form.get("fee_category_id", "").strip()
        payment_plan = request.form.get("payment_plan", "").strip()
        # Level and Session are UI filter aids (see invoice_generate.html's
        # JS, which narrows the Fee Category options to whatever's picked
        # here) — the fee_category_id is what actually determines the
        # invoice, so they're re-checked against the CHOSEN category below
        # rather than trusted on their own; a mismatch only happens if a
        # client sends inconsistent values (e.g. JS disabled/tampered).
        level = request.form.get("level", "").strip()
        academic_session = request.form.get("session", "").strip()

        # Level is only required if at least one fee category is actually
        # level-scoped (see `levels` above) — if none are, there's nothing
        # to pick, and the "All Levels" fallback option submits blank.
        error = None
        if not (academic_session and fee_category_id and payment_plan) or (levels and not level):
            error = "Level, session, fee category, and payment plan are all required."
        if error is None and payment_plan not in PAYMENT_PLANS:
            error = "Invalid payment plan."

        chosen = None
        if error is None:
            chosen = next(
                (f for f in fee_categories if str(f["fee_category_id"]) == fee_category_id),
                None,
            )
            if chosen is None:
                error = "That fee category does not apply to you."
            elif chosen["session"] != academic_session or (chosen["level"] and chosen["level"] != level):
                error = "That fee category doesn't match the level/session selected. Please try again."

        if error is None:
            existing = db.execute(
                "SELECT 1 FROM invoice WHERE student_id = ? AND fee_category_id = ? "
                "AND payment_plan = ? AND status IN ('Awaiting Payment', 'Paid')",
                (g.user["student_id"], chosen["fee_category_id"], payment_plan),
            ).fetchone()
            if existing is not None:
                error = f"You already have an invoice for {chosen['category_name']} ({payment_plan})."

        if error is None:
            amount = invoice_amount_for_plan(chosen["amount"], payment_plan)
            invoice_id = None
            for _ in range(5):
                reference = generate_payment_reference()
                try:
                    cur = db.execute(
                        "INSERT INTO invoice "
                        "(student_id, fee_category_id, payment_plan, amount, payment_reference) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (g.user["student_id"], chosen["fee_category_id"], payment_plan, amount, reference),
                    )
                    db.commit()
                    invoice_id = cur.lastrowid
                    break
                except sqlite3.IntegrityError:
                    db.rollback()
                    continue

            if invoice_id is None:
                flash("Could not generate a unique payment reference. Please try again.", "danger")
            else:
                # No flash() here on purpose: the invoice page shows a
                # one-time, self-drawing checkmark confirmation instead
                # (see invoice_view.html and DESIGN_BRIEF.md's motion
                # rules) — a generic flash banner would be a redundant
                # second "success" message on top of it.
                return redirect(url_for("student.view_invoice", invoice_id=invoice_id, generated="1"))

        if error:
            flash(error, "danger")

    # Default the Level/Session selects to the student's own level (if any
    # fee category actually offers it) and the most recent session, so the
    # Fee Category list is pre-filtered to the common case on first load —
    # the student only needs to change either select for a carried-over fee.
    default_level = g.user["level"] if g.user["level"] in levels else (levels[0] if levels else "")
    default_session = sessions[0] if sessions else ""

    return render_template(
        "student/invoice_generate.html",
        fee_categories=fee_categories,
        payment_plans=PAYMENT_PLANS,
        levels=levels,
        sessions=sessions,
        default_level=default_level,
        default_session=default_session,
    )


def _owned_invoice_or_none(db, invoice_id, student_id):
    return db.execute(
        "SELECT invoice.*, fee_category.category_name, fee_category.session, "
        "       fee_category.level, fee_category.department, fee_category.faculty "
        "FROM invoice JOIN fee_category "
        "  ON invoice.fee_category_id = fee_category.fee_category_id "
        "WHERE invoice.invoice_id = ? AND invoice.student_id = ?",
        (invoice_id, student_id),
    ).fetchone()


@bp.route("/invoices/<int:invoice_id>")
@student_required
def view_invoice(invoice_id):
    db = get_db()
    invoice = _owned_invoice_or_none(db, invoice_id, g.user["student_id"])
    if invoice is None:
        flash("Invoice not found.", "danger")
        return redirect(url_for("student.list_invoices"))
    return render_template("student/invoice_view.html", invoice=invoice, student=g.user)


@bp.route("/invoices/<int:invoice_id>/receipt")
@student_required
def view_receipt(invoice_id):
    db = get_db()
    invoice = _owned_invoice_or_none(db, invoice_id, g.user["student_id"])
    if invoice is None:
        flash("Invoice not found.", "danger")
        return redirect(url_for("student.list_invoices"))
    receipt = db.execute(
        "SELECT * FROM receipt WHERE invoice_id = ?", (invoice_id,)
    ).fetchone()
    if receipt is None:
        flash("This invoice hasn't been paid yet, so there's no receipt for it.", "danger")
        return redirect(url_for("student.view_invoice", invoice_id=invoice_id))
    return render_template(
        "student/receipt_view.html",
        invoice=invoice,
        receipt=receipt,
        student=g.user,
        amount_words=amount_in_words(invoice["amount"]),
    )


# ---------------------------------------------------------------------------
# PDF downloads — a genuine file (Content-Disposition: attachment), not the
# browser's own print-to-PDF. See app/pdf.py for why the browser-print
# pages stay as the default view rather than being replaced by this.
# ---------------------------------------------------------------------------

@bp.route("/invoices/<int:invoice_id>/pdf")
@student_required
def view_invoice_pdf(invoice_id):
    db = get_db()
    invoice = _owned_invoice_or_none(db, invoice_id, g.user["student_id"])
    if invoice is None:
        flash("Invoice not found.", "danger")
        return redirect(url_for("student.list_invoices"))
    pdf = generate_invoice_pdf(invoice, g.user)
    filename = f"invoice-{g.user['reg_number']}-{invoice_id}.pdf".replace("/", "-")
    response = Response(pdf.read(), mimetype="application/pdf")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@bp.route("/invoices/<int:invoice_id>/receipt/pdf")
@student_required
def view_receipt_pdf(invoice_id):
    db = get_db()
    invoice = _owned_invoice_or_none(db, invoice_id, g.user["student_id"])
    if invoice is None:
        flash("Invoice not found.", "danger")
        return redirect(url_for("student.list_invoices"))
    receipt = db.execute(
        "SELECT * FROM receipt WHERE invoice_id = ?", (invoice_id,)
    ).fetchone()
    if receipt is None:
        flash("This invoice hasn't been paid yet, so there's no receipt for it.", "danger")
        return redirect(url_for("student.view_invoice", invoice_id=invoice_id))
    pdf = generate_receipt_pdf(invoice, receipt, g.user, amount_in_words(invoice["amount"]))
    filename = f"receipt-{receipt['receipt_number']}.pdf".replace("/", "-")
    response = Response(pdf.read(), mimetype="application/pdf")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# ---------------------------------------------------------------------------
# Payment gateway simulator — clearly a stand-in for a real gateway (see
# module docstring). It only ever talks to handle_payment_notification();
# it holds no matching logic of its own.
# ---------------------------------------------------------------------------

@bp.route("/pay", methods=("GET", "POST"))
@student_required
def pay_simulator():
    db = get_db()
    prefill_reference = request.args.get("reference", "").strip()
    prefill_amount = ""
    if prefill_reference:
        invoice = db.execute(
            "SELECT amount FROM invoice WHERE payment_reference = ? AND status = 'Awaiting Payment'",
            (prefill_reference,),
        ).fetchone()
        if invoice is not None:
            prefill_amount = f"{invoice['amount']:.2f}"

    if request.method == "POST":
        reference = request.form.get("reference", "").strip()
        amount_paid = request.form.get("amount_paid", "").strip()

        error = None
        if not (reference and amount_paid):
            error = "Enter both a payment reference and an amount."
        amount_val = None
        if error is None:
            try:
                amount_val = float(amount_paid)
                if amount_val <= 0:
                    error = "Amount must be greater than zero."
            except ValueError:
                error = "Amount must be a number."

        if error is None:
            outcome = handle_payment_notification(db, reference, amount_val)
            if outcome["result"] == "paid":
                flash(f"Payment successful — receipt {outcome['receipt_number']} generated.", "success")
                return redirect(url_for("student.view_receipt", invoice_id=outcome["invoice"]["invoice_id"]))
            if outcome["result"] == "already_paid":
                flash("That invoice was already marked as paid.", "danger")
                return redirect(url_for("student.view_receipt", invoice_id=outcome["invoice"]["invoice_id"]))
            if outcome["result"] == "amount_mismatch":
                flash(
                    "That reference matched an invoice, but the amount paid didn't match what's "
                    "owed — this has been logged for an administrator to review.",
                    "danger",
                )
            else:
                flash(
                    "No invoice was found for that payment reference — this has been logged "
                    "for an administrator to review.",
                    "danger",
                )
        else:
            flash(error, "danger")

        prefill_reference, prefill_amount = reference, amount_paid

    return render_template(
        "student/pay_simulator.html",
        prefill_reference=prefill_reference,
        prefill_amount=prefill_amount,
    )
