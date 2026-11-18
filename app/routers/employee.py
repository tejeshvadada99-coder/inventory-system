"""
routers/employee.py
---------------------
Everything an employee can do, gated behind `Depends(require_employee)`
(admins can use these too, since the admin role is a superset):

  GET  /employee/products         -> browse the full product list
  GET  /employee/customers        -> browse known customers (name + mobile + member/points)
  GET  /employee/customers/lookup -> find a customer by mobile (auto-fills the bill form)
  PUT  /employee/customers/{id}   -> fix name/email of a customer who has no account yet
  POST /employee/bills            -> generate a bill: creates/reuses the
                                      customer, deducts stock, builds a QR
                                      code + PDF receipt, and emails it to
                                      the customer automatically

The billing endpoint is the most important one in the whole app, so it's
heavily commented below.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_employee
from app.models import Product, Customer, Bill, Sale, User
from app.schemas import ProductOut, CustomerOut, CustomerUpdate, BillCreate, BillOut
from app.utils.customer_helpers import normalize_mobile, find_customer_by_mobile, points_for_amount
from app.utils.qr_code import generate_bill_qr
from app.utils.pdf_bill import generate_bill_pdf
from app.utils.email_sender import send_bill_email
from app.config import settings

router = APIRouter(prefix="/employee", tags=["employee"], dependencies=[Depends(require_employee)])


@router.get("/products", response_model=List[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).all()


@router.get("/customers", response_model=List[CustomerOut])
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).all()


@router.get("/customers/lookup", response_model=Optional[CustomerOut])
def lookup_customer(mobile: str, db: Session = Depends(get_db)):
    """Used by the billing form: type a mobile number, get the saved customer (or null)."""
    return find_customer_by_mobile(db, mobile)


@router.put("/customers/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Customer not found")
    if customer.user_id is not None:
        raise HTTPException(400, "This customer has an account - they manage their own details")
    if payload.name is not None and payload.name.strip():
        customer.name = payload.name.strip()
    if payload.email is not None:
        customer.email = payload.email.strip().lower()
    db.commit()
    db.refresh(customer)
    return customer


@router.post("/bills", response_model=BillOut)
def create_bill(
    payload: BillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employee),
):
    if not payload.items:
        raise HTTPException(400, "A bill needs at least one item")

    # 1. Find the customer by mobile number (spaces/dashes ignored), or create a new record.
    mobile = normalize_mobile(payload.customer_mobile)
    if not mobile:
        raise HTTPException(400, "A valid mobile number is required")
    customer = find_customer_by_mobile(db, mobile)
    if not customer:
        customer = Customer(
            name=payload.customer_name,
            mobile_number=mobile,
            email=payload.customer_email,
        )
        db.add(customer)
        db.flush()  # gives `customer.id` without a full commit yet
    elif payload.customer_email and not customer.email:
        customer.email = payload.customer_email

    # 2. Create the Bill shell first so we have a bill.id for QR/PDF filenames.
    bill = Bill(customer_id=customer.id, created_by_id=current_user.id, total_amount=0.0)
    db.add(bill)
    db.flush()

    # 3. Add each line item, checking stock and deducting it as we go.
    total = 0.0
    for item in payload.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(404, f"Product id {item.product_id} not found")
        if product.quantity_in_stock < item.quantity:
            raise HTTPException(
                400,
                f"Not enough stock for '{product.name}' "
                f"(have {product.quantity_in_stock}, need {item.quantity})",
            )
        line_total = product.price * item.quantity
        db.add(Sale(
            bill_id=bill.id,
            product_id=product.id,
            quantity=item.quantity,
            unit_price=product.price,
            line_total=line_total,
        ))
        product.quantity_in_stock -= item.quantity
        total += line_total

    bill.total_amount = total

    # Loyalty: only registered members (customers with an account) earn points.
    if customer.user_id is not None:
        bill.points_earned = points_for_amount(total)
        customer.loyalty_points += bill.points_earned
    db.commit()
    db.refresh(bill)

    # 4. Generate the QR code + PDF receipt.
    qr_path = generate_bill_qr(bill.id, customer.name, bill.total_amount, settings.STORE_NAME)
    bill.qr_code_path = qr_path
    pdf_path = generate_bill_pdf(bill, settings.STORE_NAME, qr_path)

    # 5. Email it to the customer automatically, if we have an address.
    if customer.email:
        sent = send_bill_email(customer.email, customer.name, bill.id, pdf_path)
        bill.email_sent = sent

    db.commit()
    db.refresh(bill)
    return bill
