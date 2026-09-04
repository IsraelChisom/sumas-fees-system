"""
pdf.py — ReportLab PDF generation for invoices and receipts.

This does NOT replace the existing browser-print pages
(student/invoice_view.html, student/receipt_view.html) — printing straight
from the browser is still the simplest path for a student at a cyber
café, and it stays the default. This adds a genuine downloadable PDF
alongside it: a real file with the correct Content-Type and a
Content-Disposition: attachment header (same convention already used for
the Departmental Report's CSV export), not the browser's own
print-to-PDF.

The document itself deliberately mirrors the printed page's structure —
letterhead, status pill, a two-column field grid, an amount block, a
reference/receipt-number block, a footnote — in the same espresso/gold
palette as the rest of the app (DESIGN_BRIEF.md), so the PDF a student
downloads looks like it belongs to the same system as the page it came
from, not a generic ReportLab default.

Three entry points, each returning a ready-to-serve BytesIO:
  - generate_invoice_pdf(invoice, student)
  - generate_receipt_pdf(invoice, receipt, student, amount_words)
  - generate_departmental_report_pdf(rows, department, level)

Both `invoice` and `student` are sqlite3.Row objects — the same rows
student.py already fetches for the HTML views (invoice carries the
joined fee_category.category_name/session from _owned_invoice_or_none()).
`rows` for the departmental report is the same list of dicts
admin.py's _departmental_report_rows() already builds for the HTML view
and the CSV export — this PDF is a third rendering of that exact data,
not a separate query.
"""
import io
import os
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# ---------------------------------------------------------------------------
# Brand palette — lifted directly from style.css's :root custom properties,
# not reinvented for this document.
# ---------------------------------------------------------------------------
ESPRESSO = colors.HexColor("#3e2723")
GOLD = colors.HexColor("#b8935a")
MUTED = colors.HexColor("#6e5d53")
BORDER = colors.HexColor("#ded1bf")
IVORY = colors.HexColor("#faf6f0")
CREAM_TEXT = colors.HexColor("#f5efe6")
STATUS_CONFIRMED = colors.HexColor("#2f855a")
STATUS_PENDING = colors.HexColor("#b7791f")

CONTENT_WIDTH = 18 * cm

# The departmental report has eight columns of tabular data — landscape,
# with its own (wider) content width, rather than squeezing a roster into
# the portrait width the invoice/receipt documents use.
REPORT_MARGIN = 1.2 * cm
REPORT_CONTENT_WIDTH = landscape(A4)[0] - 2 * REPORT_MARGIN

# ---------------------------------------------------------------------------
# Fonts — Windows ships Arial/Times variants that include the Naira sign
# (U+20A6); ReportLab's built-in Helvetica/Times do not. Register the
# system TTFs when they're present (so amounts render as "₦150,000.00")
# and fall back to the base-14 fonts with a plain "N" prefix when they
# aren't (e.g. a non-Windows deployment) — the document must never crash
# for want of a font file, only degrade its currency symbol.
# ---------------------------------------------------------------------------
_FONTS_READY = False
_HAS_NAIRA_GLYPH = False
FONT_BODY = "Helvetica"
FONT_BODY_BOLD = "Helvetica-Bold"
FONT_BODY_ITALIC = "Helvetica-Oblique"
FONT_HEADING_BOLD = "Times-Bold"


def _register_fonts():
    global _FONTS_READY, _HAS_NAIRA_GLYPH
    global FONT_BODY, FONT_BODY_BOLD, FONT_BODY_ITALIC, FONT_HEADING_BOLD
    if _FONTS_READY:
        return
    _FONTS_READY = True

    fonts_dir = r"C:\Windows\Fonts"
    wanted = {
        "PDFSans": "arial.ttf",
        "PDFSans-Bold": "arialbd.ttf",
        "PDFSans-Italic": "ariali.ttf",
        "PDFSerif-Bold": "timesbd.ttf",
    }
    try:
        registered = {}
        for name, filename in wanted.items():
            path = os.path.join(fonts_dir, filename)
            if not os.path.exists(path):
                return  # missing any one of them -> stay on the base-14 fallback
            pdfmetrics.registerFont(TTFont(name, path))
            registered[name] = path
        FONT_BODY = "PDFSans"
        FONT_BODY_BOLD = "PDFSans-Bold"
        FONT_BODY_ITALIC = "PDFSans-Italic"
        FONT_HEADING_BOLD = "PDFSerif-Bold"
        _HAS_NAIRA_GLYPH = True
    except Exception:
        # Font registration is a presentation nicety, never a hard
        # requirement — any failure here just keeps the base-14 fallback.
        _HAS_NAIRA_GLYPH = False


def naira(amount):
    """Formats an amount with the Naira sign when a font that actually
    carries that glyph is available, otherwise a plain 'N' prefix — never
    a broken/missing-glyph box in the rendered PDF."""
    _register_fonts()
    symbol = "\u20a6" if _HAS_NAIRA_GLYPH else "N"
    return f"{symbol}{amount:,.2f}"


def _esc(value):
    return escape(str(value))


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

def _styles():
    _register_fonts()
    return {
        "title": ParagraphStyle(
            "Title", fontName=FONT_HEADING_BOLD, fontSize=13.5,
            textColor=colors.white, leading=16,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", fontName=FONT_BODY, fontSize=9.5,
            textColor=GOLD, leading=13, spaceBefore=3,
        ),
        "crest": ParagraphStyle(
            "Crest", fontName=FONT_HEADING_BOLD, fontSize=16,
            textColor=ESPRESSO, leading=20, alignment=1,
        ),
        "field_label": ParagraphStyle(
            "FieldLabel", fontName=FONT_BODY, fontSize=7.3,
            textColor=MUTED, leading=10, spaceAfter=2,
        ),
        "field_value": ParagraphStyle(
            "FieldValue", fontName=FONT_BODY_BOLD, fontSize=10.5,
            textColor=ESPRESSO, leading=13,
        ),
        "amount_label": ParagraphStyle(
            "AmountLabel", fontName=FONT_BODY, fontSize=8,
            textColor=GOLD, leading=11,
        ),
        "amount_value": ParagraphStyle(
            "AmountValue", fontName=FONT_HEADING_BOLD, fontSize=22,
            textColor=colors.white, leading=27, spaceBefore=3,
        ),
        "amount_words": ParagraphStyle(
            "AmountWords", fontName=FONT_BODY_ITALIC, fontSize=8.7,
            textColor=CREAM_TEXT, leading=12, spaceBefore=5,
        ),
        "reference_label": ParagraphStyle(
            "ReferenceLabel", fontName=FONT_BODY, fontSize=7.3,
            textColor=MUTED, leading=10, spaceAfter=3,
        ),
        "reference_value": ParagraphStyle(
            "ReferenceValue", fontName="Courier-Bold", fontSize=15,
            textColor=ESPRESSO, leading=18,
        ),
        "footnote": ParagraphStyle(
            "Footnote", fontName=FONT_BODY_ITALIC, fontSize=8.5,
            textColor=MUTED, leading=12,
        ),
        "status_confirmed": ParagraphStyle(
            "StatusConfirmed", fontName=FONT_BODY_BOLD, fontSize=9.5,
            textColor=STATUS_CONFIRMED, leading=12,
        ),
        "status_pending": ParagraphStyle(
            "StatusPending", fontName=FONT_BODY_BOLD, fontSize=9.5,
            textColor=STATUS_PENDING, leading=12,
        ),
        "right_label": ParagraphStyle(
            "RightLabel", fontName=FONT_BODY, fontSize=7.3,
            textColor=MUTED, leading=10, spaceAfter=2, alignment=TA_RIGHT,
        ),
        "right_value": ParagraphStyle(
            "RightValue", fontName=FONT_BODY_BOLD, fontSize=10.5,
            textColor=ESPRESSO, leading=13, alignment=TA_RIGHT,
        ),
        "meta": ParagraphStyle(
            "Meta", fontName=FONT_BODY, fontSize=9, textColor=MUTED, leading=12,
        ),
        "report_header": ParagraphStyle(
            "ReportHeader", fontName=FONT_BODY_BOLD, fontSize=8, textColor=colors.white,
            leading=11,
        ),
        "report_header_right": ParagraphStyle(
            "ReportHeaderRight", fontName=FONT_BODY_BOLD, fontSize=8, textColor=colors.white,
            leading=11, alignment=TA_RIGHT,
        ),
        "report_cell": ParagraphStyle(
            "ReportCell", fontName=FONT_BODY, fontSize=8.7, textColor=ESPRESSO, leading=11,
        ),
        "report_cell_muted": ParagraphStyle(
            "ReportCellMuted", fontName=FONT_BODY, fontSize=8, textColor=MUTED, leading=10.5,
        ),
        "report_amount": ParagraphStyle(
            "ReportAmount", fontName=FONT_BODY, fontSize=8.7, textColor=MUTED, leading=11,
            alignment=TA_RIGHT,
        ),
        "report_balance": ParagraphStyle(
            "ReportBalance", fontName=FONT_BODY_BOLD, fontSize=8.7, textColor=ESPRESSO,
            leading=11, alignment=TA_RIGHT,
        ),
        "report_status_paid": ParagraphStyle(
            "ReportStatusPaid", fontName=FONT_BODY_BOLD, fontSize=8.2,
            textColor=STATUS_CONFIRMED, leading=11,
        ),
        "report_status_outstanding": ParagraphStyle(
            "ReportStatusOutstanding", fontName=FONT_BODY_BOLD, fontSize=8.2,
            textColor=STATUS_PENDING, leading=11,
        ),
    }


def _letterhead(subtitle_text, content_width=CONTENT_WIDTH):
    s = _styles()
    crest = Paragraph("S", s["crest"])
    title_block = [
        Paragraph("STATE UNIVERSITY OF MEDICAL &amp; APPLIED SCIENCES", s["title"]),
        Paragraph(_esc(subtitle_text).upper(), s["subtitle"]),
    ]
    table = Table([[crest, title_block]], colWidths=[1.6 * cm, content_width - 1.6 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ESPRESSO),
        ("BACKGROUND", (0, 0), (0, 0), GOLD),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("LEFTPADDING", (1, 0), (1, 0), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return table


def _status_line(status_text, positive):
    s = _styles()
    style = s["status_confirmed"] if positive else s["status_pending"]
    dot = "\u25cf"
    return Paragraph(f"{dot} {_esc(status_text)}", style)


def _field_grid(fields):
    """Two-column label/value grid with a hairline divider between rows —
    the PDF equivalent of .print-field-grid / .print-field."""
    s = _styles()
    rows = []
    for i in range(0, len(fields), 2):
        pair = fields[i:i + 2]
        row = []
        for label, value in pair:
            row.append([
                Paragraph(_esc(label).upper(), s["field_label"]),
                Paragraph(_esc(value), s["field_value"]),
            ])
        if len(row) == 1:
            row.append("")
        rows.append(row)

    grid = Table(rows, colWidths=[CONTENT_WIDTH / 2, CONTENT_WIDTH / 2])
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("LEFTPADDING", (1, 0), (1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]
    if len(rows) > 1:
        style.append(("LINEBELOW", (0, 0), (-1, -2), 0.6, BORDER))
    grid.setStyle(TableStyle(style))
    return grid


def _amount_block(label, amount_text, words=None):
    s = _styles()
    cell = [
        Paragraph(_esc(label).upper(), s["amount_label"]),
        Paragraph(_esc(amount_text), s["amount_value"]),
    ]
    if words:
        cell.append(Paragraph(_esc(words), s["amount_words"]))
    box = Table([[cell]], colWidths=[CONTENT_WIDTH])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ESPRESSO),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
    ]))
    return box


def _reference_block(label, value):
    s = _styles()
    cell = [
        Paragraph(_esc(label).upper(), s["reference_label"]),
        Paragraph(_esc(value), s["reference_value"]),
    ]
    box = Table([[cell]], colWidths=[CONTENT_WIDTH])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), IVORY),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
    ]))
    return box


def _footnote(text):
    return Paragraph(_esc(text), _styles()["footnote"])


def _meta_line(text):
    return Paragraph(_esc(text), _styles()["meta"])


def _document(buffer):
    return SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        title="SUMAS Fees System",
    )


def _document_landscape(buffer):
    return SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        topMargin=REPORT_MARGIN, bottomMargin=REPORT_MARGIN,
        leftMargin=REPORT_MARGIN, rightMargin=REPORT_MARGIN,
        title="SUMAS Fees System",
    )


def _report_footer(canvas, doc):
    """Page number + generation timestamp, drawn on every page — the one
    place in this module that draws directly on the canvas rather than
    flowing through Platypus, since a footer needs to repeat per page
    regardless of where the table happens to break."""
    canvas.saveState()
    canvas.setFont(FONT_BODY, 7.5)
    canvas.setFillColor(MUTED)
    page_width = landscape(A4)[0]
    canvas.drawString(REPORT_MARGIN, 0.8 * cm, f"Page {doc.page}")
    canvas.drawRightString(
        page_width - REPORT_MARGIN, 0.8 * cm,
        f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    )
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

def generate_invoice_pdf(invoice, student):
    buffer = io.BytesIO()
    doc = _document(buffer)
    is_paid = invoice["status"] == "Paid"

    story = [
        _letterhead("Fees Invoice"),
        Spacer(1, 12),
        _status_line("Paid" if is_paid else "Awaiting Payment", is_paid),
        Spacer(1, 8),
        _field_grid([
            ("Student", student["full_name"]),
            ("Reg. Number", student["reg_number"]),
            ("Department", student["department"]),
            ("Faculty", student["faculty"]),
            ("Fee Category", invoice["category_name"]),
            ("Session", invoice["session"]),
            ("Payment Plan", invoice["payment_plan"]),
            ("Date Generated", invoice["date_generated"]),
        ]),
        Spacer(1, 14),
        _amount_block("Amount Payable", naira(invoice["amount"])),
        Spacer(1, 14),
        _reference_block("Payment Reference", invoice["payment_reference"]),
        Spacer(1, 16),
        _footnote(
            "Pay this exact amount using the reference number above. The moment payment is "
            "received, this invoice is marked Paid and an official receipt is generated "
            "automatically \u2014 no further action is needed from you or the Bursary office."
        ),
    ]
    doc.build(story)
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------

def generate_receipt_pdf(invoice, receipt, student, amount_words):
    buffer = io.BytesIO()
    doc = _document(buffer)
    s = _styles()

    receipt_row = Table(
        [[
            [Paragraph("RECEIPT NO.", s["field_label"]), Paragraph(_esc(receipt["receipt_number"]), s["field_value"])],
            [Paragraph("DATE ISSUED", s["right_label"]), Paragraph(_esc(receipt["date_issued"]), s["right_value"])],
        ]],
        colWidths=[CONTENT_WIDTH / 2, CONTENT_WIDTH / 2],
    )
    receipt_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LINEBELOW", (0, 0), (-1, -1), 0.6, BORDER),
    ]))

    story = [
        _letterhead("Official Payment Receipt"),
        Spacer(1, 12),
        receipt_row,
        Spacer(1, 8),
        _field_grid([
            ("Student", student["full_name"]),
            ("Reg. Number", student["reg_number"]),
            ("Department", student["department"]),
            ("Faculty", student["faculty"]),
            ("Level", f"{student['level']} Level"),
            ("Fee Category", invoice["category_name"]),
            ("Session", invoice["session"]),
            ("Payment Plan", invoice["payment_plan"]),
            ("Payment Reference", invoice["payment_reference"]),
            ("Date Paid", invoice["date_paid"]),
        ]),
        Spacer(1, 14),
        _amount_block("Amount Paid", naira(invoice["amount"]), words=amount_words),
        Spacer(1, 16),
        _footnote("This is a system-generated receipt and does not require a signature or stamp."),
    ]
    doc.build(story)
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# Departmental Report — a landscape roster, not a single-record document
# like the invoice/receipt above. Same letterhead treatment, but the body
# is a repeating-header Table rather than a field grid, since the whole
# point of this document is many rows at once (Chapter 3's "for
# export/download" requirement — see admin.py's _departmental_report_rows(),
# the one query this, the HTML view, and the CSV export all share).
# ---------------------------------------------------------------------------

_REPORT_COLUMN_FRACTIONS = [0.17, 0.12, 0.14, 0.07, 0.125, 0.125, 0.125, 0.125]


def generate_departmental_report_pdf(rows, department, level):
    buffer = io.BytesIO()
    doc = _document_landscape(buffer)
    s = _styles()

    filter_bits = []
    if department:
        filter_bits.append(department)
    if level:
        filter_bits.append(f"{level} Level")
    filter_text = " — " + ", ".join(filter_bits) if filter_bits else " — All Departments, All Levels"
    count_text = f"{len(rows)} student{'' if len(rows) == 1 else 's'}{filter_text}"

    header = [
        Paragraph("STUDENT", s["report_header"]),
        Paragraph("REG. NUMBER", s["report_header"]),
        Paragraph("DEPARTMENT", s["report_header"]),
        Paragraph("LEVEL", s["report_header"]),
        Paragraph("TOTAL OWED", s["report_header_right"]),
        Paragraph("TOTAL PAID", s["report_header_right"]),
        Paragraph("BALANCE", s["report_header_right"]),
        Paragraph("STATUS", s["report_header"]),
    ]
    data = [header]
    for row in rows:
        is_paid = row["balance"] <= 0
        status_style = s["report_status_paid"] if is_paid else s["report_status_outstanding"]
        data.append([
            Paragraph(_esc(row["full_name"]), s["report_cell"]),
            Paragraph(_esc(row["reg_number"]), s["report_cell_muted"]),
            Paragraph(_esc(row["department"]), s["report_cell"]),
            Paragraph(_esc(row["level"]), s["report_cell_muted"]),
            Paragraph(_esc(f"{row['total_owed']:,.2f}"), s["report_amount"]),
            Paragraph(_esc(f"{row['total_paid']:,.2f}"), s["report_amount"]),
            Paragraph(_esc(f"{row['balance']:,.2f}"), s["report_balance"]),
            Paragraph("Fully Paid" if is_paid else "Outstanding", status_style),
        ])

    col_widths = [f * REPORT_CONTENT_WIDTH for f in _REPORT_COLUMN_FRACTIONS]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), ESPRESSO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, GOLD),
    ]
    if len(rows) > 0:
        style.append(("LINEBELOW", (0, 1), (-1, -1), 0.5, BORDER))
    table.setStyle(TableStyle(style))
    body = [table]
    if len(rows) == 0:
        body += [Spacer(1, 14), _meta_line("No students match this filter.")]

    story = [
        _letterhead("Departmental Payment-Status Report", content_width=REPORT_CONTENT_WIDTH),
        Spacer(1, 10),
        _meta_line(count_text),
        Spacer(1, 8),
    ] + body

    doc.build(story, onFirstPage=_report_footer, onLaterPages=_report_footer)
    buffer.seek(0)
    return buffer
