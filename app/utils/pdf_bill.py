"""
utils/pdf_bill.py
------------------
Builds a simple one-page PDF receipt (itemized lines + total + QR code
image embedded at the bottom) using fpdf2. This is the file that actually
gets attached to the customer's email.
"""
import os
from fpdf import FPDF

PDF_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "bills")
os.makedirs(PDF_DIR, exist_ok=True)


def generate_bill_pdf(bill, store_name: str, qr_code_path: str) -> str:
    """
    `bill` is a models.Bill SQLAlchemy object (with .sale_lines and .customer
    already loaded). Returns the path to the generated PDF file.
    """
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, store_name, ln=True, align="C")

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Receipt #{bill.id}", ln=True)
    pdf.cell(0, 8, f"Date: {bill.created_at.strftime('%d %b %Y, %I:%M %p')}", ln=True)
    pdf.cell(0, 8, f"Customer: {bill.customer.name} ({bill.customer.mobile_number})", ln=True)
    pdf.ln(4)

    # Table header
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(80, 8, "Item", border=1)
    pdf.cell(30, 8, "Qty", border=1, align="C")
    pdf.cell(35, 8, "Unit Price", border=1, align="R")
    pdf.cell(35, 8, "Line Total", border=1, align="R")
    pdf.ln()

    pdf.set_font("Helvetica", "", 11)
    for line in bill.sale_lines:
        pdf.cell(80, 8, line.product.name, border=1)
        pdf.cell(30, 8, str(line.quantity), border=1, align="C")
        pdf.cell(35, 8, f"{line.unit_price:.2f}", border=1, align="R")
        pdf.cell(35, 8, f"{line.line_total:.2f}", border=1, align="R")
        pdf.ln()

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(145, 10, "Total", border=1)
    pdf.cell(35, 10, f"Rs. {bill.total_amount:.2f}", border=1, align="R")
    pdf.ln(16)

    if qr_code_path and os.path.exists(qr_code_path):
        pdf.image(qr_code_path, x=85, w=40)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 8, "Scan to verify this receipt", align="C")

    file_path = os.path.join(PDF_DIR, f"bill_{bill.id}.pdf")
    pdf.output(file_path)
    return file_path
