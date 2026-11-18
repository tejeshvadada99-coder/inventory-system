
"""
app/routers/customers.py
------------------------
Customer account management.

Features:
- View customer profile
- Update customer profile
- View purchase history
- View individual bill details

Customers can only access their own information.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Customer, Bill
from app.auth import get_current_customer


router = APIRouter(
    prefix="/customer",
    tags=["Customer Account"]
)


# --------------------------------------------------
# Request schemas
# --------------------------------------------------

class CustomerProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    address: Optional[str] = Field(default=None, max_length=500)


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def format_datetime(value):
    if isinstance(value, datetime):
        return value.isoformat()

    return None


def get_customer_bill_or_404(
    db: Session,
    customer_id: int,
    bill_id: int
):
    """
    Retrieve a bill only if it belongs to the logged-in customer.
    """

    bill = (
        db.query(Bill)
        .options(
            joinedload(Bill.sale_lines).joinedload("product")
        )
        .filter(
            Bill.id == bill_id,
            Bill.customer_id == customer_id
        )
        .first()
    )

    if not bill:
        raise HTTPException(
            status_code=404,
            detail="Bill not found."
        )

    return bill


def serialize_bill(bill):
    """
    Convert a bill and its sale lines into a safe response.
    """

    items = []

    for line in bill.sale_lines:
        product_name = (
            line.product.name
            if line.product
            else "Product unavailable"
        )

        items.append({
            "product_id": line.product_id,
            "product_name": product_name,
            "quantity": line.quantity,
            "unit_price": float(line.unit_price),
            "line_total": float(line.line_total)
        })

    return {
        "bill_id": bill.id,
        "date": format_datetime(bill.created_at),
        "total_amount": float(bill.total_amount),
        "items": items
    }


# --------------------------------------------------
# Customer profile
# --------------------------------------------------

@router.get("/profile")
def get_customer_profile(
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Get the logged-in customer's profile.
    """

    return {
        "id": current_customer.id,
        "name": current_customer.name,
        "email": current_customer.email,
        "mobile_number": current_customer.mobile_number,
        "address": current_customer.address,
        "email_verified": current_customer.email_verified,
        "mobile_verified": current_customer.mobile_verified,
        "loyalty_points": current_customer.loyalty_points,
        "created_at": format_datetime(current_customer.created_at)
    }


# --------------------------------------------------
# Update customer profile
# --------------------------------------------------

@router.patch("/profile")
def update_customer_profile(
    payload: CustomerProfileUpdate,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Update the logged-in customer's name and address.

    Email and mobile number are not editable here because
    changing them requires a separate verification workflow.
    """

    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one field to update."
        )

    if "name" in updates:
        if updates["name"] is not None:
            updates["name"] = updates["name"].strip()

            if len(updates["name"]) < 2:
                raise HTTPException(
                    status_code=400,
                    detail="Name must contain at least 2 characters."
                )

    if "address" in updates and updates["address"] is not None:
        updates["address"] = updates["address"].strip()

    for field, value in updates.items():
        setattr(current_customer, field, value)

    try:
        db.commit()
        db.refresh(current_customer)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to update customer profile."
        )

    return {
        "message": "Profile updated successfully.",
        "profile": {
            "id": current_customer.id,
            "name": current_customer.name,
            "email": current_customer.email,
            "mobile_number": current_customer.mobile_number,
            "address": current_customer.address
        }
    }


# --------------------------------------------------
# Purchase history
# --------------------------------------------------

@router.get("/purchase-history")
def get_purchase_history(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Get only the logged-in customer's purchase history.
    """

    query = db.query(Bill).filter(
        Bill.customer_id == current_customer.id
    )

    total_bills = query.count()

    bills = (
        query
        .order_by(Bill.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "customer_id": current_customer.id,
        "total_bills": total_bills,
        "page": page,
        "limit": limit,
        "total_pages": (total_bills + limit - 1) // limit,
        "purchases": [
            serialize_bill(bill)
            for bill in bills
        ]
    }


# --------------------------------------------------
# Individual bill details
# --------------------------------------------------

@router.get("/bills/{bill_id}")
def get_customer_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Get an individual bill belonging to the logged-in customer.

    A customer cannot view another customer's bill.
    """

    bill = get_customer_bill_or_404(
        db,
        current_customer.id,
        bill_id
    )

    return serialize_bill(bill)
