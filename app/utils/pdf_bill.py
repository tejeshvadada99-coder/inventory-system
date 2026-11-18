
"""
utils/pdf_bill.py
-----------------
Generates a professional PDF receipt using fpdf2.

Features:
- Store name and bill details
- Customer information
- Itemized product table
- Automatic page breaks
- Indian currency display (Rs.)
- QR code verification image
- Safe handling of long product names
"""

import os
from datetime import datetime
from fpdf import FPDF


PDF_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "static", "bills")
)

os.makedirs(PDF_DIR, exist_ok=True)


class BillPDF(FPDF):

    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(35, 45, 65)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0,
            8,
            f"Page {self.page_no()}",
            align="C"
        )


def generate_bill_pdf(bill, store_name: str, qr_code_path: str) -> str:
    """
    Generate a PDF receipt for a SQLAlchemy Bill object.

    Expected relationships:
        bill.customer
        bill.sale_lines
        line.product

    Returns:
        Absolute path to the generated PDF.
    """

    pdf = BillPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # --------------------------------------------------
    # Store heading
    # --------------------------------------------------

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(25, 45, 75)
    pdf.cell(0, 12, str(store_name or "STORE"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, "SALES RECEIPT", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)

    # --------------------------------------------------
    # Bill information
    # --------------------------------------------------

    pdf.set_text_color(30, 30, 30)
    pdf.set_font("Helvetica", "", 10)

    bill_date = bill.created_at

    if isinstance(bill_date, datetime):
        formatted_date = bill_date.strftime("%d %b %Y, %I:%M %p")
    else:
        formatted_date = "Not available"

    customer = getattr(bill, "customer", None)

    customer_name = getattr(customer, "name", None) or "Walk-in Customer"
    customer_mobile = getattr(customer, "mobile_number", None) or "Not provided"

    pdf.cell(0, 7, f"Receipt Number: #{bill.id}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Date: {formatted_date}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Customer: {customer_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Mobile: {customer_mobile}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)

    # --------------------------------------------------
    # Product table
    # --------------------------------------------------

    col_widths = [80, 25, 40, 40]
    row_height = 8

    def draw_table_header():
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(225, 232, 242)
        pdf.set_text_color(25, 45, 75)

        headers = ["Item", "Qty", "Unit Price", "Line Total"]

        for header, width in zip(headers, col_widths):
            pdf.cell(
                width,
                row_height,
                header,
                border=1,
                align="C",
                fill=True
            )

        pdf.ln()

    draw_table_header()

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(30, 30, 30)

    sale_lines = getattr(bill, "sale_lines", []) or []

    for line in sale_lines:

        product = getattr(line, "product", None)
        product_name = getattr(product, "name", None) or "Unknown Product"

        quantity = getattr(line, "quantity", 0)
        unit_price = getattr(line, "unit_price", 0)
        line_total = getattr(line, "line_total", 0)

        # Wrap long product names.
        name_width = col_widths[0] - 2

        name_lines = pdf.multi_cell(
            name_width,
            5,
            str(product_name),
            dry_run=True,
            output="LINES"
        )

        row_lines = max(1, len(name_lines))
        current_row_height = row_lines * 5

        # Start a new page if the complete row will not fit.
        if pdf.get_y() + current_row_height > pdf.page_break_trigger:

            pdf.add_page()
            draw_table_header()

            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(30, 30, 30)

        x = pdf.get_x()
        y = pdf.get_y()

        # Product name
        pdf.multi_cell(
            col_widths[0],
            5,
            str(product_name),
            border=1
        )

        # Quantity
        pdf.set_xy(x + col_widths[0], y)
        pdf.cell(
            col_widths[1],
            current_row_height,
            str(quantity),
            border=1,
            align="C"
        )

        # Unit price
        pdf.cell(
            col_widths[2],
            current_row_height,
            f"Rs. {float(unit_price or 0):.2f}",
            border=1,
            align="R"
        )

        # Line total
        pdf.cell(
            col_widths[3],
            current_row_height,
            f"Rs. {float(line_total or 0):.2f}",
            border=1,
            align="R"
        )

        pdf.set_xy(pdf.l_margin, y + current_row_height)

    # --------------------------------------------------
    # Grand total
    # --------------------------------------------------

    if pdf.get_y() + 15 > pdf.page_break_trigger:
        pdf.add_page()

    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(235, 240, 247)

    pdf.cell(
        sum(col_widths[:-1]),
        10,
        "GRAND TOTAL",
        border=1,
        fill=True
    )

    pdf.cell(
        col_widths[-1],
        10,
        f"Rs. {float(bill.total_amount or 0):.2f}",
        border=1,
        align="R",
        fill=True
    )

    pdf.ln(12)

    # --------------------------------------------------
    # QR code
    # --------------------------------------------------

    if qr_code_path and os.path.isfile(qr_code_path):

        qr_size = 35

        if pdf.get_y() + qr_size + 15 > pdf.page_break_trigger:
            pdf.add_page()

        qr_x = (pdf.w - qr_size) / 2
        qr_y = pdf.get_y()

        pdf.image(
            qr_code_path,
            x=qr_x,
            y=qr_y,
            w=qr_size,
            h=qr_size
        )

        pdf.set_y(qr_y + qr_size + 3)

        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(90, 90, 90)

        pdf.cell(
            0,
            7,
            "Scan to verify this receipt",
            align="C"
        )

    # --------------------------------------------------
    # Save PDF
    # --------------------------------------------------

    file_path = os.path.join(PDF_DIR, f"bill_{bill.id}.pdf")

    pdf.output(file_path)

    return file_path
