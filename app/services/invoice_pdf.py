"""
Invoice PDF Generator

Generates downloadable PDF invoices for billing records.
Uses ReportLab (already in requirements.txt).
"""
import io
import logging

from app.models.billing import BillingRecord
from app.models.tenant import Tenant

logger = logging.getLogger("unihr.invoice")


def generate_invoice_pdf(record: BillingRecord, tenant: Tenant) -> io.BytesIO:
    """Generate a single-page invoice PDF for a billing record."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    story = []

    # ── Header ──
    title_style = ParagraphStyle("InvoiceTitle", parent=styles["Title"], fontSize=24, textColor=colors.HexColor("#1e40af"))
    story.append(Paragraph("INVOICE", title_style))
    story.append(Spacer(1, 4 * mm))

    # ── Company & Invoice Info ──
    info_data = [
        ["UniHR SaaS", f"Invoice #: {record.invoice_number or 'N/A'}"],
        ["", f"Date: {record.created_at.strftime('%Y-%m-%d') if record.created_at else 'N/A'}"],
        ["", f"Status: {record.status.upper()}"],
    ]
    info_table = Table(info_data, colWidths=[300, 230])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, 0), colors.HexColor("#1e40af")),
        ("FONTSIZE", (0, 0), (0, 0), 14),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 8 * mm))

    # ── Bill To ──
    story.append(Paragraph("Bill To:", ParagraphStyle("BillTo", parent=styles["Normal"], fontSize=10, textColor=colors.grey)))
    story.append(Paragraph(tenant.name or str(tenant.id), styles["Heading3"]))
    story.append(Spacer(1, 8 * mm))

    # ── Line Items ──
    period_str = ""
    if record.period_start and record.period_end:
        period_str = f"{record.period_start.strftime('%Y-%m-%d')} ~ {record.period_end.strftime('%Y-%m-%d')}"

    items_header = ["Description", "Plan", "Period", "Amount"]
    items_data = [
        items_header,
        [
            record.description or "Subscription",
            (record.plan or "").capitalize(),
            period_str or "-",
            f"${float(record.amount_usd):.2f} {record.currency}",
        ],
    ]
    items_table = Table(items_data, colWidths=[200, 80, 130, 120])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 6 * mm))

    # ── Total ──
    total_data = [
        ["", "", "Total:", f"${float(record.amount_usd):.2f} {record.currency}"],
    ]
    total_table = Table(total_data, colWidths=[200, 80, 130, 120])
    total_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("TEXTCOLOR", (2, 0), (2, 0), colors.HexColor("#1e40af")),
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (-2, 0), (-2, -1), "RIGHT"),
        ("LINEABOVE", (2, 0), (-1, 0), 1, colors.HexColor("#1e40af")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 15 * mm))

    # ── Footer ──
    footer_style = ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    story.append(Paragraph("Thank you for your business. This invoice was generated automatically by UniHR.", footer_style))
    story.append(Paragraph("Questions? Contact support.", footer_style))

    doc.build(story)
    buf.seek(0)
    return buf
