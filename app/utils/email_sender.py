
"""
utils/email_sender.py
----------------------
Handles:
1. Customer bill PDF emails.
2. Customer email verification codes.

SMTP settings are loaded from app.config.settings.
"""

import smtplib
from email.message import EmailMessage

from app.config import settings


def _send_email(msg: EmailMessage) -> bool:
    """
    Shared SMTP email delivery function.

    Supports:
    - SMTP with STARTTLS (commonly port 587)
    - SMTP over SSL (commonly port 465)
    """

    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        print("[email_sender] SMTP not configured.")
        return False

    try:
        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=20
            ) as server:
                server.login(
                    settings.SMTP_USERNAME,
                    settings.SMTP_PASSWORD
                )
                server.send_message(msg)

        else:
            with smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=20
            ) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()

                server.login(
                    settings.SMTP_USERNAME,
                    settings.SMTP_PASSWORD
                )

                server.send_message(msg)

        return True

    except Exception as exc:
        print(f"[email_sender] Failed to send email: {exc}")
        return False


# ==================================================
# BILL PDF EMAIL
# ==================================================

def send_bill_email(
    to_email: str,
    customer_name: str,
    bill_id: int,
    pdf_path: str
) -> bool:

    msg = EmailMessage()

    msg["Subject"] = (
        f"Your receipt #{bill_id} from {settings.STORE_NAME}"
    )

    msg["From"] = (
        f"{settings.SMTP_FROM_NAME} "
        f"<{settings.SMTP_USERNAME}>"
    )

    msg["To"] = to_email

    msg.set_content(
        f"Hi {customer_name},\n\n"
        f"Thanks for shopping with us! "
        f"Your receipt #{bill_id} is attached.\n\n"
        f"— {settings.STORE_NAME}"
    )

    try:
        with open(pdf_path, "rb") as file:
            msg.add_attachment(
                file.read(),
                maintype="application",
                subtype="pdf",
                filename=f"receipt_{bill_id}.pdf",
            )

        return _send_email(msg)

    except Exception as exc:
        print(
            f"[email_sender] Unable to prepare receipt email: {exc}"
        )
        return False


# ==================================================
# CUSTOMER EMAIL VERIFICATION
# ==================================================

def send_customer_verification_email(
    to_email: str,
    customer_name: str,
    verification_code: str
) -> bool:

    msg = EmailMessage()

    msg["Subject"] = (
        f"Verify your email - {settings.STORE_NAME}"
    )

    msg["From"] = (
        f"{settings.SMTP_FROM_NAME} "
        f"<{settings.SMTP_USERNAME}>"
    )

    msg["To"] = to_email

    expiry_minutes = (
        settings.CUSTOMER_VERIFICATION_EXPIRE_MINUTES
    )

    msg.set_content(
        f"Hello {customer_name},\n\n"
        f"Thank you for registering with {settings.STORE_NAME}.\n\n"
        f"Your email verification code is:\n\n"
        f"{verification_code}\n\n"
        f"This code expires in {expiry_minutes} minutes.\n\n"
        f"If you did not request this verification, "
        f"you can ignore this email.\n\n"
        f"Regards,\n"
        f"{settings.STORE_NAME}"
    )

    return _send_email(msg)
