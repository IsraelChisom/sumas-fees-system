# SUMAS Fees Project — Briefing for Claude Code

Read this file fully before making any changes. This project is a B.Sc. final-year
project (Eze Ezekiel, SUMAS/2022/0697) built in an earlier chat conversation with
Claude, following a formal Chapter 1–3 academic writeup that already exists as
Word documents. Your job is to continue building it, matching the conventions
already established.

## Project

"Design and Development of a Web-Based School Fees Payment Tracking and Receipt
System" — a Flask web app for State University of Medical and Applied Sciences
(SUMAS). Two user roles only: **Student** and **Administrator**.

**The workflow (redesigned — this replaced an earlier "submit a claim, admin
verifies it by eye" design that the supervisor rejected as just a digital copy
of the manual process):** modeled on a real system used at the University of
Nigeria, Nsukka. A student generates an **Invoice** for a level, session, fee
category, and payment plan, gets a unique **payment reference** (modeled on Remita's RRR),
and pays that reference externally. The moment a payment notification for that
reference arrives — for a real gateway, a webhook; for this project, a clearly
labeled **payment gateway simulator**, since there's no real gateway access —
the invoice is matched and marked Paid **automatically**, and an **Official
Receipt** is generated automatically. No admin action in the normal path. An
admin's only remaining role in payments is a small **exception queue**:
notifications that couldn't be auto-matched (wrong reference, or the right
reference but the wrong amount), which an admin manually resolves.

## Tech stack (fixed — do not change without asking)

- **Flask** (application factory pattern in `app/__init__.py`)
- **SQLite**, accessed via raw `sqlite3` (no ORM) — see `app/db.py` and `schema.sql`.
  SQLite was deliberately chosen over MySQL for zero-config simplicity; this is
  documented and justified in Chapter 3 of the report, so don't "upgrade" to
  MySQL/Postgres without being asked.
- **ReportLab** is in `requirements.txt` and now used — `app/pdf.py` generates
  a genuine downloadable PDF for both invoices and receipts (see "What's
  already built and tested" item 10). The print-ready HTML pages (browser
  Print / Save-as-PDF via `window.print()`, `@media print` rules in
  `style.css`) stay as the default view — the PDF is a second, explicit
  "Download PDF" option alongside them, not a replacement.
- Plain HTML/Jinja2 templates. No JS framework, no build step, no npm — the one
  exception is the small vanilla `fetch()` script in `admin/claims_list.html`-
  style pages when one exists (see DESIGN_BRIEF.md's motion rules); this is
  still plain browser JS, not a framework. Keep it that way — this is a
  single-developer academic project, not a production SaaS.
- **Visual design** follows `DESIGN_BRIEF.md` in the project root — the
  espresso-brown/ivory/gold institutional palette, Lora + IBM Plex Sans
  typography, and the specific motion rules. That file is authoritative;
  the "Design system" section below is a short summary only. Every new page
  built in the invoice/payment redesign follows it (letterhead-style invoice
  and receipt documents, ledger-style tables, the self-drawing-checkmark and
  receipt-reveal motion moments).

## Design system (fixed — follow this for every new page, do not invent a new look)

**See `DESIGN_BRIEF.md` for the full, authoritative visual design brief**
(espresso-brown/tan/gold/ivory institutional palette, Lora + IBM Plex Sans
fonts, the ledger/letterhead/official-document motifs, and the specific,
purposeful motion rules — no generic AI-dashboard decoration). Short
summary of the mechanics:

- **Bootstrap 5.3** loaded via CDN in `base.html` (CSS + the JS bundle), plus
  **Bootstrap Icons** via CDN for icons (`<i class="bi bi-...">`). No npm,
  no build step — just the CDN `<link>`/`<script>` tags already in
  `base.html`. Restyled fully per `DESIGN_BRIEF.md` — it should never look
  like default Bootstrap.
- **Google Fonts "Lora"** (headings) and **"IBM Plex Sans"** (body/data/
  tables), loaded via CDN `<link>` in `base.html`'s `<head>`, applied via
  CSS variables in `app/static/css/style.css`. Never fall back to a
  system font.
- Brand colors and every restyled component live in `style.css` as CSS
  custom properties re-themed on top of Bootstrap's own CSS-variable API
  (`--bs-primary`, `--bs-link-color`, etc.), rather than one-off colors in
  templates. New components should use Bootstrap classes (`btn-primary`,
  `badge`, `alert`, `table`, `card`, ...) which pick up the palette
  automatically; only add a new custom CSS rule in `style.css` when
  Bootstrap has no equivalent (e.g. `.stat-tile`, `.sidebar`,
  `.badge-status-*`, `.print-document`).
- **Layout**: `base.html` supports three layouts via `{% set layout = ... %}`
  in a child template (set right after `{% extends "base.html" %}`):
  - `'admin'` — left sidebar (Dashboard / Students / Fees / Unmatched
    Payments, with Reports as a disabled "Soon" placeholder) + top navbar.
    Use this for every new admin-facing page.
  - `'plain'` — no navbar/sidebar at all, full-bleed centered layout; used
    only by the login page.
  - default (`'app'`) — top navbar, plain centered container, no sidebar;
    used by student-facing pages, including the invoice and receipt
    documents.
- **Flash messages** render as dismissible Bootstrap alerts
  (`app/templates/_flashes.html`), color-coded from the category passed to
  `flash(message, category)` in Python — always pass `"success"` for a
  success message and `"danger"` for an error; don't call bare `flash(msg)`
  without a category, or it won't be color-coded correctly. Two specific
  student actions (generating an invoice, paying via the simulator/
  receiving a receipt) deliberately skip flash() in favour of the
  self-drawing-checkmark / receipt-reveal motion moments instead — see
  DESIGN_BRIEF.md and the comments in `app/student.py`.
- **Status badges**: `badge-status-pending` (amber, e.g. "Awaiting Payment"),
  `badge-status-confirmed` (green, "Paid"), `badge-status-rejected` (red,
  used for the exception queue's unresolved count) — defined in `style.css`,
  functional/conventional colors, never brown-tinted per DESIGN_BRIEF.md.
- Keep pages responsive (usable on a laptop screen at minimum) — Bootstrap's
  grid/utility classes already handle this; the sidebar collapses to a
  horizontal scrollable bar under `991.98px`.

## Database schema (`schema.sql`)

Six tables: `student`, `administrator`, `fee_category`, `invoice`, `receipt`,
`unmatched_payment`.

Important business rule for `fee_category`: `category_name` is one of
`'School Fees'`, `'Departmental Fee'`, `'Faculty Fee'`.
- School Fees → `department` and `faculty` both NULL (applies to everyone)
- Departmental Fee → `department` populated, `faculty` NULL
- Faculty Fee → `faculty` populated, `department` NULL

`fee_category` is also scoped by `level` (added after the initial build, once
it became clear tuition realistically varies by level — e.g. School Fees
commonly charges more at 100 Level than at 200–400 Level). `level` is
nullable: NULL means "applies to every level" (the default for Departmental/
Faculty Fee, which don't have to vary), while a specific value (`'100'`..
`'400'`, matching `student.level`'s free-text values) scopes that row to just
that level. Any of the three category types may use either. A student's
Outstanding Balance and the admin's Departmental Report only ever show fee
categories matching the student's *own* registered level (or level-
independent ones) — see `_applicable_fee_categories()` in `app/student.py`.
The invoice-generation form is the one place level is **selectable** rather
than fixed to the student's own record: `generate_invoice()` uses the wider
`_fee_categories_for_invoice_form()` (no level filter) so a student can still
invoice a level other than their current one — e.g. a fee carried over from
an earlier session — with the Level and Academic Session fields filtering the
Fee Category options client-side and the chosen category re-validated
server-side against whatever level/session was actually submitted.

**Known gotcha already fixed once:** SQLite's `UNIQUE` constraint does NOT catch
duplicates when the differentiating column is NULL (NULL ≠ NULL in SQL). See
`_normalise_fee_scope()` and the explicit `IS`-based duplicate check in
`app/admin.py`'s `add_fee()` (now also checking `level IS ?`, alongside
`department`/`faculty`) — replicate this pattern anywhere else duplicate
detection involves a nullable column.

**`invoice`** — one row per (student, fee category, payment plan) the student
has generated a reference for. `payment_plan` is `'Full Payment'` |
`'First Installment'` | `'Second Installment'`; the two installments split
`fee_category.amount` evenly, with the second absorbing any odd kobo (see
`invoice_amount_for_plan()` in `app/payments.py`). `payment_reference` is a
unique 12-digit numeric string (Remita RRR-shaped), generated with a
generate-and-retry loop, not derived from the row's id. `status` is
`'Awaiting Payment'` until `handle_payment_notification()` matches a payment
to it, then `'Paid'`. A student may not hold two unresolved-or-paid invoices
for the same (fee_category, payment_plan) — enforced in `generate_invoice()`.
Cross-plan rules (e.g. blocking Full Payment once an installment exists) are
NOT enforced — a known, deliberate v1 simplification.

**`receipt`** — one row per invoice, created only by
`handle_payment_notification()` the instant it marks an invoice Paid, never
any other way. `amount_in_words` is NOT stored — it's computed at render time
by `amount_in_words()` in `app/payments.py`, and the student's/school's
details are joined at render time too, not snapshotted. This mirrors the
project's existing "never store what can be recomputed" principle (see the
outstanding-balance note below) — a receipt can never go stale relative to
the invoice or student record it describes.

**`unmatched_payment`** — the admin exception queue. A row is created by
`handle_payment_notification()` whenever a payment notification's reference
matches no invoice, or matches one but the amount is wrong. `resolved` is
0/1 (SQLite has no BOOLEAN). An admin resolves a row either by **matching**
it (enter the correct reference; this re-runs the payment through
`handle_payment_notification()` — the SAME function a real notification
would use) or by **dismissing** it outright. See `app/admin.py`'s
`match_unmatched()` / `dismiss_unmatched()`.

A student's outstanding balance is still **never stored** — it's computed
at query time (`student.py`'s `view_balance()`) as
`fee_category.amount - SUM(invoice.amount WHERE status='Paid')` for that
student/category/session (the same principle as before, just `invoice`
instead of the old `payment_claim`).

## `app/payments.py` — the payment-matching core

`handle_payment_notification(db, reference, amount_paid)` is the single
function every payment notification flows through — the gateway simulator
(`student.py`'s `pay_simulator()`) and an admin's manual "match" both call it,
and it does not know or care which one is calling it. That's deliberate, for
the project's technical credibility (a real gateway integration later would
mean a new route calling this same function, not rewriting it). It returns
one of four outcomes: `"paid"` (marks the invoice Paid + creates the receipt,
as one transaction — `db.rollback()` on failure, nothing partially commits),
`"already_paid"` (harmless no-op, never double-receipts), `"amount_mismatch"`
or `"unmatched"` (both log to `unmatched_payment` for the admin queue).

Also in that module: `generate_payment_reference()` (12-digit RRR-shaped
string), `invoice_amount_for_plan()` (splits a fee by payment plan), and
`amount_in_words()` (a hand-rolled number-to-Naira-words converter — no
external package — e.g. `56000` → `"Fifty Six Thousand Naira Only"`).

## What's already built and tested (do not regress these)

1. **Authentication module** (`app/auth.py`) — student login via `reg_number`,
   admin login via `staff_id`, hashed passwords (`werkzeug.security`), session-
   based role separation via `session['user_type']`. Decorators:
   `login_required`, `student_required`, `admin_required`. Tested in
   `smoke_test_auth.py` (6 tests).
2. **Student & Fee Management** (`app/admin.py`, routes `/admin/students*` and
   `/admin/fees*`) — admin can add/edit students, add/edit fee categories with
   the scoping rule above enforced both in a Python helper and at the DB level.
   Tested in `smoke_test_admin.py` (12 tests).
3. **Invoice generation** (`app/student.py`) — student picks a level, session,
   fee category (scoped to them, same rule as fee management), and payment
   plan, gets a unique payment reference. Tested in `smoke_test_invoices.py`.
4. **Payment gateway simulator + automatic matching** (`app/student.py`,
   `app/payments.py`) — clearly labeled as a simulation; calls
   `handle_payment_notification()`. Auto-generates the receipt. Tested in
   `smoke_test_payments.py` (13 tests).
5. **Student invoice/receipt history + printable documents**
   (`student/invoices_list.html`, `invoice_view.html`, `receipt_view.html`) —
   a UNN-style history table with Print Invoice / Print Receipt per row;
   ownership enforced (`_owned_invoice_or_none()`).
6. **Admin exception queue** (`app/admin.py`'s `list_unmatched()` /
   `match_unmatched()` / `dismiss_unmatched()`) — the only payment screen an
   admin still uses. Tested in `smoke_test_exceptions.py` (15 tests).
7. **View outstanding balance** (`student.py`'s `view_balance()`,
   `student/balance.html`) — a "Statement of Account" ledger table, one row
   per applicable fee category: amount owed, amount paid (`SUM(invoice.amount
   WHERE status='Paid')` for that category), and the balance, plus a totals
   row. Recomputed on every request, never stored — same principle as
   receipts. An invoice still `'Awaiting Payment'` does not count toward
   "paid" yet. Tested in `smoke_test_balance.py` (12 tests).
8. **Departmental Reporting** (`admin.py`'s `departmental_report()` /
   `departmental_report_export()`, `admin/departmental_report.html`) — a
   payment-status roster filterable by department and/or level (both
   optional; either or neither can be blank). One row per matching student:
   total owed / total paid / balance, reusing `student.py`'s
   `_balance_rows()` (imported, not reimplemented) summed across every fee
   category applicable to that student, plus a Fully Paid/Outstanding badge.
   "For export/download" is two real things, not one: **Print / Save as
   PDF** (browser print, same convention as invoices/receipts) and a
   genuine **CSV file download** (`Content-Disposition: attachment`, built
   with the standard-library `csv` module — no new dependency) — pick
   whichever is more useful to actually email to a Head of Department, who
   never logs into the system themselves. Both respect the same filters.
   The sidebar's "Reports" link (previously a disabled "Soon" placeholder)
   now points here. A third export option, a genuine ReportLab PDF
   (`departmental_report_pdf()`, landscape, repeating table header via
   `Table(..., repeatRows=1)`, page-number/generated-timestamp footer
   drawn via `onFirstPage`/`onLaterPages`), was added alongside Print and
   CSV — see item 10 below, which covers both this and the invoice/
   receipt PDFs. Tested in `smoke_test_reporting.py` (24 tests).
9. **Search Payment Records** (`admin.py`'s `search_payments()`,
   `admin/payment_search.html`) — the last item from the original
   functional-requirements list. A lookup, not a report: searches the
   `invoice` table (every invoice IS a payment record — "Awaiting Payment"
   is a pending one, "Paid" is a completed one with its receipt) by
   student name, registration number, or payment reference (`LIKE` match
   across all three, `_payment_search_rows()`), optionally narrowed by
   status. Each row shows the fee category/session/plan, reference,
   amount, a status badge (with the receipt number shown under "Paid"),
   and the relevant date. No CSV/print — unlike Departmental Reporting,
   this isn't a document handed to anyone. Sidebar link "Search Payments"
   added next to Unmatched Payments. Tested in `smoke_test_search.py`
   (13 tests).
10. **ReportLab PDFs for invoices, receipts, and the Departmental Report**
    (`app/pdf.py`) — real, genuine PDF files (`Content-Disposition:
    attachment`), not the browser's own print-to-PDF. None of these
    replace the existing browser-print pages — those stay the default,
    since printing straight from the browser is still simplest at a
    cyber café — each is a second, downloadable option alongside the
    page it came from ("Download PDF" buttons on `invoice_view.html`,
    `receipt_view.html`, and `admin/departmental_report.html`).
    - `generate_invoice_pdf()` / `generate_receipt_pdf()`
      (`student.py`'s `view_invoice_pdf()` / `view_receipt_pdf()`) — a
      single-record, portrait document mirroring the printed page's own
      structure (letterhead, status pill, field grid, amount block,
      reference/receipt-number block, footnote). Both routes reuse the
      exact same ownership check (`_owned_invoice_or_none()`) as their
      HTML counterparts. Tested in `smoke_test_pdf.py` (15 tests).
    - `generate_departmental_report_pdf()` (`admin.py`'s
      `departmental_report_pdf()`) — a landscape, multi-row roster
      instead: a repeating-header `Table` (`repeatRows=1`) built from
      the exact same `_departmental_report_rows()` the HTML view and CSV
      export already share, with a page-number/generated-timestamp
      footer drawn per page via `onFirstPage`/`onLaterPages`. Tested in
      `smoke_test_reporting.py` (see item 8 above).

    All three are built with ReportLab's Platypus layer
    (`SimpleDocTemplate` plus `Table`/`Paragraph` flowables) in the same
    espresso/gold palette as the rest of the app, not a generic
    default-styled report. Windows' bundled Arial/Times TTFs are
    registered at runtime so the Naira sign renders correctly —
    `app/pdf.py`'s `naira()` falls back to a plain "N" prefix if those
    font files aren't present (e.g. a non-Windows deployment) rather
    than crashing or showing a broken glyph box.
11. **Final polish: custom 404/500 error pages, and a favicon**
    (`app/__init__.py`'s `handle_404()` / `handle_500()`, registered via
    `app.register_error_handler`; `errors/error.html`) — a stale link or
    an unexpected bug during a demo now shows a branded page instead of
    Flask's plain default one. The page reuses the login page's own
    `.auth-page`/`.auth-card`/`.auth-brand` markup rather than inventing
    a second "empty state" look, with a status code, a message, and a
    "Return to your Dashboard" / "Return to Login" button that's computed
    from the current session (student, admin, or logged out) via a shared
    `_home_url_and_label()` helper — also now used by `index()`, replacing
    its own copy of the same role check. **Note**: with `run.py`'s
    `debug=True`, Werkzeug's interactive debugger intercepts a real
    unhandled exception before `handle_500()` is reached — it only
    renders on a production-style run with debug off; `smoke_test_errors.py`
    calls it directly for that reason, documented in its own docstring.
    The favicon (`app/static/favicon.svg`, hand-authored; `favicon.ico`,
    a Pillow-generated multi-size fallback for older browsers) reuses the
    student navbar's crest motif — a bordered espresso square with a gold
    serif "S" — rather than a new mark. Tested in `smoke_test_errors.py`
    (9 tests).

Run all ten smoke test files after any change — they must keep passing:
`python smoke_test_auth.py`, `smoke_test_admin.py`, `smoke_test_invoices.py`,
`smoke_test_payments.py`, `smoke_test_exceptions.py`, `smoke_test_balance.py`,
`smoke_test_reporting.py`, `smoke_test_search.py`, `smoke_test_pdf.py`,
`smoke_test_errors.py`.
Follow the same style
for new modules: a `smoke_test_<module>.py` using Flask's test client
(`app.test_client()`), a temp SQLite file (`tempfile.mkstemp()` — do NOT use
`:memory:`, it breaks across Flask's per-request `g` connections), plain
`[PASS]`/`[FAIL]` printed lines, and a non-zero exit code on any failure.
Always include at least one test proving role-based access control is
enforced on any new route. **After changing `schema.sql`, also re-run
`python seed.py`** to rebuild `instance/sumas.sqlite` with the new shape —
`smoke_test_auth.py` uses that real file (no `DATABASE` override) rather
than a temp one, so it'll fail with "no such table" until you do.

## Full functional requirements (Chapter 3, Section 3.1.1 — as redesigned this session; the Word-doc chapters still describe the old claim/verify workflow and need updating separately, outside this codebase) — build order

**Student:**
- [x] Log in
- [x] Generate an invoice (level + session + fee category + payment plan →
      payment reference)
- [x] Pay via the gateway simulator (stands in for a real gateway)
- [x] View invoice/receipt history, with current status
- [x] View/print/download a receipt (browser print, and now a real
      ReportLab PDF download alongside it)
- [x] View outstanding balance

**Administrator:**
- [x] Log in
- [x] Add/manage student records
- [x] Create/manage fee structures
- [x] Review the payment exception queue (unmatched references, amount
      mismatches) — match to the correct invoice, or dismiss
- [x] Search payment records
- [x] Generate a payment-status report, filterable by department and level,
      for export/download (NOT a login for the Head of Department — HOD never
      logs into the system; the admin generates the report and sends it out)

## Next modules to build, in order

Every item from the original functional-requirements list (Chapter 3,
Section 3.1.1) is now built, the ReportLab PDF enhancement covers all
three documents that used to be browser-print-only (invoices, receipts,
the Departmental Report — item 10), and a final polish pass added custom
404/500 error pages and a favicon (item 11). There is no open item left
in this document. Wait for the next explicit request rather than
guessing what to build next.

## Non-functional requirements to keep honoring

- **Security:** every admin-only route needs `@admin_required`; every
  student-only route needs `@student_required`. Never trust `request.form`
  data for identifying *which* student an invoice belongs to — always derive
  it from `g.user`/the session, never from a hidden form field. Ownership is
  also checked on every invoice/receipt view (`_owned_invoice_or_none()`) so
  one student can never view another's invoice by guessing its id. The
  payment-matching path itself (`handle_payment_notification()`) is
  deliberately NOT ownership-scoped — a real gateway wouldn't know or care
  who's paying, only that the reference and amount matched.
- **Reliability:** a matched payment must update `invoice.status` and create
  the `receipt` row as a single transaction (`db.execute(...)` calls followed
  by one `db.commit()`; roll back and change nothing if either statement
  fails) — see `handle_payment_notification()` in `app/payments.py`.
- **Usability:** keep each page focused on one task, matching the existing
  templates' plain, uncluttered style.

## The person you're working with

Eze Ezekiel is a non-technical student — do not assume familiarity with git,
terminals, or programming concepts. Explain plainly, avoid jargon, and prefer
showing him what changed and how to test it over technical explanations of
implementation details, unless he asks.
