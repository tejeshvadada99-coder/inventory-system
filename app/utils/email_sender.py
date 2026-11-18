"""
utils/email_sender.py
----------------------
Sends the bill PDF to the customer's email automatically using SMTP
(configured via .env — works with Gmail, Outlook, or any SMTP provider).

This is called from routers/employee.py right after a bill is created.
`send_plain_email` is also used for member alerts (new offers, restocks).
If SMTP isn't configured yet, it fails quietly and logs a warning instead
of crashing the billing flow — the employee can still see/download the bill.
"""
import smtplib
from email.message import EmailMessage

from app.config import settings


def send_bill_email(to_email: str, customer_name: str, bill_id: int, pdf_path: str) -> bool:
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        print("[email_sender] SMTP not configured — skipping email send.")
        return False

    msg = EmailMessage()
    msg["Subject"] = f"Your receipt #{bill_id} from {settings.STORE_NAME}"
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USERNAME}>"
    msg["To"] = to_email
    msg.set_content(
        f"Hi {customer_name},\n\n"
        f"Thanks for shopping with us! Your receipt #{bill_id} is attached.\n\n"
        f"— {settings.STORE_NAME}"
    )

    with open(pdf_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=f"receipt_{bill_id}.pdf",
        )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as exc:
        print(f"[email_sender] Failed to send email: {exc}")
        return False


def send_plain_email(to_email: str, subject: str, body: str) -> bool:
    """Sends a simple text email (no attachment). Never raises - returns True/False."""
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USERNAME}>"
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as exc:
        print(f"[email_sender] Failed to send alert to {to_email}: {exc}")
        return False
