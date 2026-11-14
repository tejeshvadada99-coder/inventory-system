
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Offer, Product


GREETING_WORDS = {"hi", "hello", "hey", "hola", "namaste"}


def get_bot_reply(message: str, db: Session) -> str:
    text = message.lower().strip()

    # --- Timings ---
    if any(word in text for word in ["timing", "time", "open", "close", "hours"]):
        return (
            f"We're open daily from {settings.STORE_OPEN_TIME} to "
            f"{settings.STORE_CLOSE_TIME}. See you soon!"
        )

    # --- Offers ---
    if any(word in text for word in ["offer", "discount", "deal", "sale", "promo"]):
        offers = db.query(Offer).filter(Offer.active == True).all()  # noqa: E712
        if not offers:
            return "There are no special offers running right now — check back soon!"
        lines = [f"• {o.title}: {o.description}" for o in offers]
        return "Here are today's offers:\n" + "\n".join(lines)

    # --- Stock / availability ---
    if any(word in text for word in ["stock", "available", "have", "in stock"]):
        # Try to find a product name mentioned in the message
        products = db.query(Product).all()
        matches = [p for p in products if p.name.lower() in text]
        if matches:
            lines = [
                f"• {p.name}: {'In stock (' + str(p.quantity_in_stock) + ')' if p.quantity_in_stock > 0 else 'Out of stock'}"
                for p in matches
            ]
            return "\n".join(lines)
        return (
            "Tell me the product name and I'll check stock for you — "
            "for example: 'is coffee available?'"
        )

    # --- Greetings ---
    if any(word in text for word in GREETING_WORDS):
        return (
            f"Hi there! Welcome to {settings.STORE_NAME}. "
            "Ask me about today's offers, our timings, or whether an item is in stock."
        )

    # --- Fallback ---
    return (
        "I can help with our daily offers, store timings, or product stock — "
        "try asking something like 'what are today's offers?' or 'when do you close?'"
    )
