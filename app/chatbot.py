
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Offer,
    Product,
    Customer,
    Bill,
)


GREETING_WORDS = {
    "hi",
    "hello",
    "hey",
    "hola",
    "namaste",
}


def get_bot_reply(
    message: str,
    db: Session,
    customer: Customer = None
) -> str:

    text = message.lower().strip()
    words = set(text.split())

    # ----------------------------------------------
    # GREETINGS
    # ----------------------------------------------

    if words.intersection(GREETING_WORDS):
        greeting = (
            f"Hi there! Welcome to {settings.STORE_NAME}. "
            "Ask me about our offers, timings or product availability."
        )

        if customer:
            greeting = (
                f"Hello {customer.name}! Welcome back to "
                f"{settings.STORE_NAME}. How can I help you today?"
            )

        return greeting

    # ----------------------------------------------
    # STORE TIMINGS
    # ----------------------------------------------

    if any(word in text for word in [
        "timing",
        "time",
        "open",
        "close",
        "hours"
    ]):
        return (
            f"We're open daily from {settings.STORE_OPEN_TIME} "
            f"to {settings.STORE_CLOSE_TIME}. See you soon!"
        )

    # ----------------------------------------------
    # CUSTOMER PURCHASE HISTORY
    # ----------------------------------------------

    if customer and any(phrase in text for phrase in [
        "purchase history",
        "purchase details",
        "my purchases",
        "my orders",
        "previous purchases",
        "previous bills",
        "recent purchases",
        "my bills",
    ]):

        bills = (
            db.query(Bill)
            .filter(Bill.customer_id == customer.id)
            .order_by(Bill.created_at.desc())
            .limit(5)
            .all()
        )

        if not bills:
            return "You haven't made any purchases with us yet."

        lines = ["Here are your recent purchases:"]

        for bill in bills:
            date = (
                bill.created_at.strftime("%d-%m-%Y")
                if bill.created_at else "Date unavailable"
            )

            lines.append(
                f"Bill #{bill.id} | {date} | "
                f"Total: ₹{bill.total_amount:.2f}"
            )

            for sale in bill.sale_lines:
                lines.append(
                    f"  • {sale.product.name} "
                    f"x {sale.quantity}"
                )

        return "\n".join(lines)

    # ----------------------------------------------
    # CUSTOMER LOYALTY POINTS
    # ----------------------------------------------

    if customer and any(phrase in text for phrase in [
        "loyalty points",
        "reward points",
        "my points",
        "my rewards",
        "points balance",
    ]):
        return (
            f"You currently have "
            f"{customer.loyalty_points} loyalty points."
        )

    # ----------------------------------------------
    # OFFERS
    # ----------------------------------------------

    if any(word in text for word in [
        "offer",
        "discount",
        "deal",
        "sale",
        "promo"
    ]):

        offers = (
            db.query(Offer)
            .filter(Offer.active.is_(True))
            .all()
        )

        if not offers:
            return (
                "There are no special offers running right now. "
                "Please check back soon!"
            )

        lines = [
            f"• {offer.title}: {offer.description}"
            for offer in offers
        ]

        return "Here are our active offers:\n" + "\n".join(lines)

    # ----------------------------------------------
    # PRODUCT STOCK / AVAILABILITY
    # ----------------------------------------------

    if any(word in text for word in [
        "stock",
        "available",
        "availability",
        "have",
        "in stock"
    ]):

        products = db.query(Product).all()

        matches = [
            product
            for product in products
            if product.name.lower() in text
        ]

        if matches:
            lines = []

            for product in matches:
                if product.quantity_in_stock > 0:
                    availability = (
                        f"In stock "
                        f"({product.quantity_in_stock} available)"
                    )
                else:
                    availability = "Currently out of stock"

                lines.append(
                    f"• {product.name}: {availability}"
                )

            return "\n".join(lines)

        return (
            "Please tell me the product name so I can check "
            "its availability. For example: "
            "'Is coffee available?'"
        )

    # ----------------------------------------------
    # FALLBACK
    # ----------------------------------------------

    if customer:
        return (
            f"I'm here to help, {customer.name}! "
            "You can ask about our offers, store timings, "
            "product availability, purchase history "
            "or loyalty points."
        )

    return (
        "I can help with our daily offers, store timings "
        "and product availability. "
        "Try asking 'What are today's offers?' "
        "or 'When do you close?'"
    )
