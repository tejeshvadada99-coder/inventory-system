"""
utils/customer_helpers.py
--------------------------
Small helpers shared by the auth, employee, admin, customer and chatbot
code, so the same rules (how a mobile number is matched, how loyalty
points and tiers work) live in exactly one place.
"""
import re
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Customer


def normalize_mobile(raw: str) -> str:
    """'98765 43210', '98765-43210' and '9876543210' all become '9876543210'."""
    raw = (raw or "").strip()
    plus = "+" if raw.startswith("+") else ""
    return plus + re.sub(r"\D", "", raw)


def find_customer_by_mobile(db: Session, mobile: str):
    """Finds a customer by mobile, ignoring spaces/dashes/brackets in what's stored."""
    target = normalize_mobile(mobile)
    if not target:
        return None
    stored = Customer.mobile_number
    for ch in (" ", "-", "(", ")"):
        stored = func.replace(stored, ch, "")
    return db.query(Customer).filter(stored == target).first()


def points_for_amount(amount: float) -> int:
    return int(amount // settings.LOYALTY_SPEND_PER_POINT)


def tier_info(points: int) -> dict:
    """Returns the member's tier and how far they are from the next one."""
    if points >= settings.GOLD_POINTS:
        return {"tier": "Gold", "next_tier": None, "points_to_next": 0, "progress": 100}
    if points >= settings.SILVER_POINTS:
        span = settings.GOLD_POINTS - settings.SILVER_POINTS
        return {
            "tier": "Silver", "next_tier": "Gold",
            "points_to_next": settings.GOLD_POINTS - points,
            "progress": int((points - settings.SILVER_POINTS) / span * 100),
        }
    return {
        "tier": "Bronze", "next_tier": "Silver",
        "points_to_next": settings.SILVER_POINTS - points,
        "progress": int(points / settings.SILVER_POINTS * 100),
    }
