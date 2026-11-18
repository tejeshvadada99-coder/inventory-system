
"""
utils/qr_code.py
-----------------
Generates a QR code image for a bill.

Saves images to:
app/static/qrcodes/bill_<id>.png

The QR code contains a readable receipt summary.
"""

import os
import qrcode


QR_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "static", "qrcodes")
)

os.makedirs(QR_DIR, exist_ok=True)


def generate_bill_qr(
    bill_id: int,
    customer_name: str,
    total_amount: float,
    store_name: str
) -> str:
    """
    Creates a QR code image and returns its absolute file path.
    """

    if bill_id is None or int(bill_id) <= 0:
        raise ValueError("A valid bill ID is required.")

    customer_name = str(customer_name or "Walk-in Customer")
    store_name = str(store_name or "STORE")
    total_amount = float(total_amount)

    if total_amount < 0:
        raise ValueError("Bill total cannot be negative.")

    payload = (
        f"{store_name}\n"
        f"Receipt #{int(bill_id)}\n"
        f"Customer: {customer_name}\n"
        f"Total: Rs. {total_amount:.2f}"
    )

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4
    )

    qr.add_data(payload)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    file_path = os.path.join(
        QR_DIR,
        f"bill_{int(bill_id)}.png"
    )

    image.save(file_path)

    return file_path
