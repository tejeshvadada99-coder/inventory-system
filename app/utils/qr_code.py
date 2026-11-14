"""
utils/qr_code.py
-----------------
Generates a QR code image for a bill and saves it to
app/static/qrcodes/bill_<id>.png so it can be:
  1. shown on-screen to the employee right after billing
  2. attached to the email sent to the customer

The QR code encodes a short, human-readable receipt summary. In production
you'd typically encode a URL to a hosted receipt page instead — swap the
`payload` string below for that if you add one.
"""
import os
import qrcode

QR_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "qrcodes")
os.makedirs(QR_DIR, exist_ok=True)


def generate_bill_qr(bill_id: int, customer_name: str, total_amount: float, store_name: str) -> str:
    """Creates the QR image and returns its file path on disk."""
    payload = (
        f"{store_name}\n"
        f"Receipt #{bill_id}\n"
        f"Customer: {customer_name}\n"
        f"Total: Rs. {total_amount:.2f}"
    )
    img = qrcode.make(payload)

    file_path = os.path.join(QR_DIR, f"bill_{bill_id}.png")
    img.save(file_path)
    return file_path
