
"""
app/routers/loyalty.py
----------------------
Customer loyalty management.

Features:
- View loyalty balance
- View earned points
- View redeemed points
- View loyalty transaction history
- View individual transaction details

Points must be awarded by trusted billing logic,
not directly by customer requests.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, LoyaltyTransaction
from app.auth import get_current_customer


router = APIRouter(
    prefix="/customer/loyalty",
    tags=["Customer Loyalty"]
)


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def serialize_transaction(transaction):
    return {
        "id": transaction.id,
        "customer_id": transaction.customer_id,
        "bill_id": transaction.bill_id,
        "points": transaction.points,
        "transaction_type": transaction.transaction_type,
        "description": transaction.description,
        "created_at": (
            transaction.created_at.isoformat()
            if transaction.created_at
            else None
        )
    }


# --------------------------------------------------
# Loyalty balance
# --------------------------------------------------

@router.get("/balance")
def get_loyalty_balance(
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Get the logged-in customer's current loyalty balance.
    """

    return {
        "customer_id": current_customer.id,
        "customer_name": current_customer.name,
        "available_points": current_customer.loyalty_points or 0
    }


# --------------------------------------------------
# Loyalty summary
# --------------------------------------------------

@router.get("/summary")
def get_loyalty_summary(
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Get total earned, redeemed and available points.
    """

    transactions = db.query(LoyaltyTransaction).filter(
        LoyaltyTransaction.customer_id == current_customer.id
    ).all()

    total_earned = 0
    total_redeemed = 0

    for transaction in transactions:
        points = int(transaction.points or 0)

        transaction_type = str(
            transaction.transaction_type
        ).lower()

        if transaction_type == "earned":
            total_earned += points

        elif transaction_type == "redeemed":
            total_redeemed += abs(points)

    return {
        "customer_id": current_customer.id,
        "available_points": current_customer.loyalty_points or 0,
        "total_earned": total_earned,
        "total_redeemed": total_redeemed
    }


# --------------------------------------------------
# Transaction history
# --------------------------------------------------

@router.get("/transactions")
def get_loyalty_transactions(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Get the logged-in customer's loyalty transaction history.
    """

    query = db.query(LoyaltyTransaction).filter(
        LoyaltyTransaction.customer_id == current_customer.id
    )

    total_transactions = query.count()

    transactions = (
        query
        .order_by(LoyaltyTransaction.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "customer_id": current_customer.id,
        "available_points": current_customer.loyalty_points or 0,
        "total_transactions": total_transactions,
        "page": page,
        "limit": limit,
        "total_pages": (
            total_transactions + limit - 1
        ) // limit,
        "transactions": [
            serialize_transaction(transaction)
            for transaction in transactions
        ]
    }


# --------------------------------------------------
# Individual transaction
# --------------------------------------------------

@router.get("/transactions/{transaction_id}")
def get_loyalty_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Get an individual transaction.

    Customers can only access their own transactions.
    """

    transaction = db.query(LoyaltyTransaction).filter(
        LoyaltyTransaction.id == transaction_id,
        LoyaltyTransaction.customer_id == current_customer.id
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail="Loyalty transaction not found."
        )

    return serialize_transaction(transaction)
