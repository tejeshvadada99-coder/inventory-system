"""
chatbot.py
----------
A simple, free, rule-based chatbot (no external AI API, no extra cost).
It looks for keywords in the message and answers using LIVE data from the
database - active offers, stock levels, and store timings from .env.

Two audiences:
  - Guests      -> offers (public ones only), timings, stock.
  - Signed-in customers -> the same, plus PERSONAL answers: their loyalty
                  points, their recent orders, and members-only offers.
                  The chat route passes in the logged-in user to switch this on.

To make this smarter later, this is the one file you'd swap for an LLM call.
"""
from typing import Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Offer, Product, Customer, Bill, User, RoleEnum
from app.utils.customer_helpers import tier_info

GREETING_WORDS = {"hi", "hello", "hey", "hola", "namaste"}
SIGN_IN_HINT = "Sign in from the Customer tab on the homepage and I can answer that for you."


def _member_for(user: Optional[User], db: Session) -> Optional[Customer]:
    if user and user.role == RoleEnum.customer:
        return db.query(Customer).filter(Customer.user_id == user.id).first()
    return None


def get_bot_reply(message: str, db: Session, user: Optional[User] = None) -> str:
    text = message.lower().strip()
    member = _member_for(user, db)
    first_name = member.name.split()[0] if member else None

    # --- Personal: loyalty points ---
    if any(w in text for w in ["point", "loyalty", "reward", "tier", "member"]) and "offer" not in text:
        if not member:
            return "Members earn loyalty points on every purchase. " + SIGN_IN_HINT
        info = tier_info(member.loyalty_points)
        reply = f"{first_name}, you have {member.loyalty_points} points - {info['tier']} tier."
        if info["next_tier"]:
            reply += f" {info['points_to_next']} more points to reach {info['next_tier']}."
        return reply

    # --- Personal: orders / purchase history ---
    if any(w in text for w in ["my order", "last order", "my purchase", "my bill", "history", "receipt", "orders"]):
        if not member:
            return "I can show your recent purchases. " + SIGN_IN_HINT
        bills = (
            db.query(Bill).filter(Bill.customer_id == member.id)
            .order_by(Bill.created_at.desc()).limit(3).all()
        )
        if not bills:
            return "You don't have any purchases yet. Your bills will appear here after your first visit."
        lines = [
            f"- Receipt #{b.id}, {b.created_at.strftime('%d %b %Y')}: Rs. {b.total_amount:.2f}"
            for b in bills
        ]
        return "Your latest purchases:\n" + "\n".join(lines) + "\nOpen 'Purchases' to see items and download PDFs."

    # --- Timings ---
    if any(word in text for word in ["timing", "time", "open", "close", "hours"]):
        return (
            f"We're open daily from {settings.STORE_OPEN_TIME} to "
            f"{settings.STORE_CLOSE_TIME}. See you soon!"
        )

    # --- Offers (members also see members-only ones) ---
    if any(word in text for word in ["offer", "discount", "deal", "sale", "promo"]):
        query = db.query(Offer).filter(Offer.active == True)  # noqa: E712
        if not member:
            query = query.filter(Offer.members_only == False)  # noqa: E712
        offers = query.all()
        if not offers:
            return "There are no special offers running right now - check back soon!"
        lines = [
            f"- {o.title}{' (members only)' if o.members_only else ''}: {o.description}"
            for o in offers
        ]
        reply = "Here are today's offers:\n" + "\n".join(lines)
        if not member:
            reply += "\nRegister as a customer to unlock members-only offers."
        return reply

    # --- Stock / availability ---
    if any(word in text for word in ["stock", "available", "have", "in stock"]):
        products = db.query(Product).all()
        matches = [p for p in products if p.name.lower() in text]
        if matches:
            lines = [
                f"- {p.name}: {'In stock (' + str(p.quantity_in_stock) + ')' if p.quantity_in_stock > 0 else 'Out of stock'}"
                for p in matches
            ]
            return "\n".join(lines)
        return (
            "Tell me the product name and I'll check stock for you - "
            "for example: 'is coffee available?'"
        )

    # --- Greetings ---
    if any(word in text.split() for word in GREETING_WORDS):
        who = f" {first_name}" if first_name else ""
        return (
            f"Hi{who}! Welcome to {settings.STORE_NAME}. "
            "Ask me about today's offers, our timings, or whether an item is in stock."
            + (" You can also ask about your points or your last order." if member else "")
        )

    # --- Fallback ---
    return (
        "I can help with our daily offers, store timings, or product stock - "
        "try asking something like 'what are today's offers?' or 'when do you close?'"
        + (" Members can also ask 'my points' or 'my last order'." if member else "")
    )
