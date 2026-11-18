"""
utils/alerts.py
----------------
Email alerts for registered customers who left "alerts" switched on:
  - a new offer was published
  - a product that was out of stock is available again

Two steps, kept apart on purpose:
  1. `get_alert_recipients(db)`  -> read who to email (needs the database)
  2. `send_alerts(...)`          -> do the slow emailing (no database needed)
The routers run step 2 as a FastAPI BackgroundTask, so the admin's request
returns instantly even if email is slow or blocked on the free Render plan.
"""
from typing import List, Tuple
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Customer
from app.utils.email_sender import send_plain_email


def get_alert_recipients(db: Session) -> List[Tuple[str, str]]:
    rows = db.query(Customer).filter(
        Customer.user_id.isnot(None),
        Customer.alerts_enabled.is_(True),
        Customer.email.isnot(None),
    ).all()
    return [(c.name, c.email) for c in rows if c.email]


def send_alerts(recipients: List[Tuple[str, str]], subject: str, message: str) -> None:
    for name, email in recipients:
        body = (
            f"Hi {name.split()[0]},\n\n{message}\n\n"
            f"- {settings.STORE_NAME}\n"
            "(You can turn these alerts off from your Profile page.)"
        )
        send_plain_email(email, f"{settings.STORE_NAME}: {subject}", body)
