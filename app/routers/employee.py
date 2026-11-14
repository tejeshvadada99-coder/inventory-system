
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_employee
from app.models import Product, Customer, Bill, Sale, User
from app.schemas import ProductOut, CustomerOut, BillCreate, BillOut
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


@router.post("/bills", response_model=BillOut)
def create_bill(
    payload: BillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employee),
):
    if not payload.items:
        raise HTTPException(400, "A bill needs at least one item")

    # 1. Find the customer by mobile number, or create a new record.
    customer = db.query(Customer).filter(Customer.mobile_number == payload.customer_mobile).first()
    if not customer:
        customer = Customer(
            name=payload.customer_name,
            mobile_number=payload.customer_mobile,
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
