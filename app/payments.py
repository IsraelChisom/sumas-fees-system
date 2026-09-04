"""
payments.py — Payment matching and receipt-support logic shared by every
route that can produce a "a payment happened" event: the payment gateway
simulator (student.py's pay_simulator()) today, and in a real deployment,
a real gateway's webhook tomorrow.

The whole point of `handle_payment_notification()` is that it does not
know or care who called it. It takes a payment reference and an amount,
and does exactly what a real Remita webhook handler would do: look up the
matching invoice, and either mark it paid (generating a receipt in the
same transaction) or file it in the admin exception queue for manual
review. Nothing about its signature or behaviour is simulator-specific —
swapping the simulator for a real gateway integration later would mean
adding a new route that calls this same function, not rewriting it.
"""
import random
import sqlite3


def generate_payment_reference():
    """A 12-digit numeric reference, the same shape as Remita's RRR."""
    return "".join(str(random.randint(0, 9)) for _ in range(12))


def invoice_amount_for_plan(fee_amount, payment_plan):
    """Splits a fee_category's full amount according to the chosen
    payment plan. Full Payment is the whole amount; the two installments
    split it evenly, with the second installment absorbing any odd kobo
    so the two halves always sum exactly back to the full amount."""
    fee_amount = float(fee_amount)
    first_half = round(fee_amount / 2, 2)
    if payment_plan == "Full Payment":
        return round(fee_amount, 2)
    if payment_plan == "First Installment":
        return first_half
    if payment_plan == "Second Installment":
        return round(fee_amount - first_half, 2)
    return None


_ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
    "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen",
    "Eighteen", "Nineteen",
]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _three_digit_words(n):
    """n is 0..999."""
    words = []
    if n >= 100:
        words.append(_ONES[n // 100] + " Hundred")
        n %= 100
        if n > 0:
            words.append("and")
    if n >= 20:
        words.append(_TENS[n // 10])
        if n % 10:
            words.append(_ONES[n % 10])
    elif n > 0:
        words.append(_ONES[n])
    return " ".join(words)


def _int_to_words(n):
    if n == 0:
        return "Zero"
    scales = [(1_000_000_000, "Billion"), (1_000_000, "Million"), (1_000, "Thousand"), (1, "")]
    parts = []
    remaining = n
    for scale, name in scales:
        if remaining >= scale:
            count, remaining = divmod(remaining, scale)
            chunk = _three_digit_words(count)
            parts.append(f"{chunk} {name}".strip())
    return " ".join(parts)


def amount_in_words(amount):
    """e.g. 56000 -> 'Fifty Six Thousand Naira Only';
    56000.50 -> 'Fifty Six Thousand Naira, Fifty Kobo Only'."""
    amount = float(amount)
    naira = int(amount)
    kobo = round((amount - naira) * 100)
    words = _int_to_words(naira) + " Naira"
    if kobo:
        words += f", {_int_to_words(kobo)} Kobo"
    words += " Only"
    return words


def handle_payment_notification(db, reference, amount_paid):
    """The single entry point every payment notification — simulated or
    (eventually) real — flows through. Returns a dict describing what
    happened:
      {"result": "paid",            "invoice": Row, "receipt_number": str}
      {"result": "already_paid",    "invoice": Row}
      {"result": "amount_mismatch", "invoice": Row}
      {"result": "unmatched"}
    "amount_mismatch" and "unmatched" both land the notification in the
    admin exception queue (unmatched_payment) for manual review; "paid"
    and "already_paid" never do.
    """
    invoice = db.execute(
        "SELECT * FROM invoice WHERE payment_reference = ?", (reference,)
    ).fetchone()

    if invoice is None:
        db.execute(
            "INSERT INTO unmatched_payment (reference_received, amount_received) VALUES (?, ?)",
            (reference, amount_paid),
        )
        db.commit()
        return {"result": "unmatched"}

    if invoice["status"] == "Paid":
        # A harmless duplicate notification for something already settled
        # (e.g. a gateway retry) — never double-mark or double-receipt.
        return {"result": "already_paid", "invoice": invoice}

    if round(float(invoice["amount"]), 2) != round(float(amount_paid), 2):
        # The reference matched, but the amount didn't — don't silently
        # accept it. File it for a human to look at instead.
        db.execute(
            "INSERT INTO unmatched_payment (reference_received, amount_received) VALUES (?, ?)",
            (reference, amount_paid),
        )
        db.commit()
        return {"result": "amount_mismatch", "invoice": invoice}

    # Reliability NFR (unchanged from the old claims workflow): the status
    # update and the receipt creation happen as one transaction — if
    # either statement fails, nothing is committed.
    receipt_number = f"RCT-{invoice['invoice_id']:06d}"
    try:
        db.execute(
            "UPDATE invoice SET status = 'Paid', date_paid = datetime('now') WHERE invoice_id = ?",
            (invoice["invoice_id"],),
        )
        db.execute(
            "INSERT INTO receipt (invoice_id, receipt_number) VALUES (?, ?)",
            (invoice["invoice_id"], receipt_number),
        )
        db.commit()
    except sqlite3.Error:
        db.rollback()
        raise

    invoice = db.execute(
        "SELECT * FROM invoice WHERE invoice_id = ?", (invoice["invoice_id"],)
    ).fetchone()
    return {"result": "paid", "invoice": invoice, "receipt_number": receipt_number}
