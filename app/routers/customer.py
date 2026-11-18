"""
routers/customer.py
--------------------
Everything a logged-in CUSTOMER can do, gated by `require_customer`.
A customer can only ever see their own data - every query is filtered by
the customer record linked to the logged-in user.

  GET  /customer/me                 -> profile, loyalty points, tier, totals
  PUT  /customer/me                 -> change name / email / alert preference
  GET  /customer/bills              -> purchase history (newest first)
  GET  /customer/bills/{id}/pdf     -> download a saved bill as PDF
  GET  /customer/bills/{id}/qr      -> the bill's QR code image
  GET  /customer/offers             -> active offers, including members-only

Render's free plan wipes files on restart, so the PDF/QR endpoints
re-create a missing file from the database on demand.
"""
import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.auth import require_customer
from app.models import User, Customer, Bill, Offer
from app.schemas import ProfileUpdate, OfferOut
from app.utils.customer_helpers import tier_info
from app.utils.qr_code import generate_bill_qr
from app.utils.pdf_bill import generate_bill_pdf, PDF_DIR

router = APIRouter(prefix="/customer", tags=["customer"])


def _my_customer(user: User, db: Session) -> Customer:
    customer = db.query(Customer).filter(Customer.user_id == user.id).first()
    if not customer:
        raise HTTPException(404, "Customer profile not found")
    return customer


def _my_bill(bill_id: int, customer: Customer, db: Session) -> Bill:
    bill = db.query(Bill).filter(Bill.id == bill_id, Bill.customer_id == customer.id).first()
    if not bill:
        raise HTTPException(404, "Bill not found")
    return bill


def _profile(customer: Customer, db: Session) -> dict:
    total_spent, bill_count = db.query(
        func.coalesce(func.sum(Bill.total_amount), 0.0), func.count(Bill.id)
    ).filter(Bill.customer_id == customer.id).one()
    return {
        "full_name": customer.name,
        "email": customer.email,
        "mobile_number": customer.mobile_number,
        "alerts_enabled": customer.alerts_enabled,
        "loyalty_points": customer.loyalty_points,
        "total_spent": float(total_spent),
        "bills_count": int(bill_count),
        "spend_per_point": settings.LOYALTY_SPEND_PER_POINT,
        "silver_points": settings.SILVER_POINTS,
        "gold_points": settings.GOLD_POINTS,
        **tier_info(customer.loyalty_points),
    }


@router.get("/me")
def my_profile(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    return _profile(_my_customer(user, db), db)


@router.put("/me")
def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    customer = _my_customer(user, db)

    if payload.full_name is not None:
        name = payload.full_name.strip()
        if len(name) < 2:
            raise HTTPException(400, "Please enter your full name")
        customer.name = name
        user.full_name = name

    if payload.email is not None:
        email = payload.email.strip().lower()
        taken = db.query(User).filter(func.lower(User.email) == email, User.id != user.id).first()
        if taken:
            raise HTTPException(400, "That email is already used by another account")
        # `username` is left alone on purpose: it's inside the login token, so
        # changing it would sign the customer out. Login also accepts the new email.
        user.email = email
        customer.email = email

    if payload.alerts_enabled is not None:
        customer.alerts_enabled = payload.alerts_enabled

    db.commit()
    return _profile(customer, db)


@router.get("/bills")
def my_bills(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    customer = _my_customer(user, db)
    bills = db.query(Bill).filter(Bill.customer_id == customer.id).order_by(Bill.created_at.desc()).all()
    return [
        {
            "id": b.id,
            "total_amount": b.total_amount,
            "points_earned": b.points_earned,
            "created_at": b.created_at,
            "items": [
                {
                    "product_name": line.product.name,
                    "quantity": line.quantity,
                    "unit_price": line.unit_price,
                    "line_total": line.line_total,
                }
                for line in b.sale_lines
            ],
        }
        for b in bills
    ]


def _ensure_files(bill: Bill):
    """Returns (qr_path, pdf_path), re-creating either if the file has gone missing."""
    qr_path = bill.qr_code_path
    if not qr_path or not os.path.exists(qr_path):
        qr_path = generate_bill_qr(bill.id, bill.customer.name, bill.total_amount, settings.STORE_NAME)
    pdf_path = os.path.join(PDF_DIR, f"bill_{bill.id}.pdf")
    if not os.path.exists(pdf_path):
        pdf_path = generate_bill_pdf(bill, settings.STORE_NAME, qr_path)
    return qr_path, pdf_path


@router.get("/bills/{bill_id}/pdf")
def bill_pdf(bill_id: int, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    bill = _my_bill(bill_id, _my_customer(user, db), db)
    _, pdf_path = _ensure_files(bill)
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"receipt_{bill.id}.pdf")


@router.get("/bills/{bill_id}/qr")
def bill_qr(bill_id: int, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    bill = _my_bill(bill_id, _my_customer(user, db), db)
    qr_path, _ = _ensure_files(bill)
    return FileResponse(qr_path, media_type="image/png")


@router.get("/offers", response_model=List[OfferOut])
def my_offers(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    return db.query(Offer).filter(Offer.active.is_(True)).order_by(Offer.members_only.desc(), Offer.id.desc()).all()
