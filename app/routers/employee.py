
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    BackgroundTasks,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.auth import require_employee

from app.models import (
    Product,
    Customer,
    Bill,
    Sale,
    User,
)

from app.schemas import (
    ProductOut,
    CustomerOut,
    BillCreate,
    BillOut,
)

from app.utils.qr_code import generate_bill_qr
from app.utils.pdf_bill import generate_bill_pdf
from app.utils.email_sender import send_bill_email

from app.config import settings


router = APIRouter(
    prefix="/employee",
    tags=["employee"],
    dependencies=[Depends(require_employee)]
)


# ==================================================
# PRODUCTS
# ==================================================

@router.get("/products", response_model=List[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).all()


# ==================================================
# CUSTOMERS
# ==================================================

@router.get("/customers", response_model=List[CustomerOut])
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).order_by(
        Customer.created_at.desc()
    ).all()


# ==================================================
# BACKGROUND EMAIL
# ==================================================

def _email_in_background(
    bill_id: int,
    to_email: str,
    customer_name: str,
    pdf_path: str,
):
    """
    Sends the bill PDF after the billing response.
    Updates the email_sent field after attempting delivery.
    """

    sent = send_bill_email(
        to_email,
        customer_name,
        bill_id,
        pdf_path
    )

    db = SessionLocal()

    try:
        bill = db.query(Bill).filter(
            Bill.id == bill_id
        ).first()

        if bill:
            bill.email_sent = sent
            db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ==================================================
# CREATE BILL
# ==================================================

@router.post(
    "/bills",
    response_model=BillOut,
    status_code=status.HTTP_201_CREATED
)
def create_bill(
    payload: BillCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employee),
):
    if not payload.items:
        raise HTTPException(
            400,
            "A bill needs at least one item"
        )

    try:
        # ------------------------------------------
        # 1. Find or create customer
        # ------------------------------------------

        customer = db.query(Customer).filter(
            Customer.mobile_number == payload.customer_mobile
        ).first()

        if not customer:
            customer = Customer(
                name=payload.customer_name,
                mobile_number=payload.customer_mobile,
                email=payload.customer_email,
            )

            # No password or login account is created here.
            # This preserves employee-created customers.

            db.add(customer)
            db.flush()

        elif payload.customer_email and not customer.email:
            customer.email = payload.customer_email

        # ------------------------------------------
        # 2. Create bill
        # ------------------------------------------

        bill = Bill(
            customer_id=customer.id,
            created_by_id=current_user.id,
            total_amount=0.0,
        )

        db.add(bill)
        db.flush()

        # ------------------------------------------
        # 3. Add sale items and update stock
        # ------------------------------------------

        total = 0.0

        for item in payload.items:

            product = (
                db.query(Product)
                .filter(Product.id == item.product_id)
                .with_for_update()
                .first()
            )

            if not product:
                raise HTTPException(
                    404,
                    f"Product id {item.product_id} not found"
                )

            if product.quantity_in_stock < item.quantity:
                raise HTTPException(
                    400,
                    f"Not enough stock for '{product.name}' "
                    f"(have {product.quantity_in_stock}, "
                    f"need {item.quantity})"
                )

            line_total = product.price * item.quantity

            sale = Sale(
                bill_id=bill.id,
                product_id=product.id,
                quantity=item.quantity,
                unit_price=product.price,
                line_total=line_total,
            )

            db.add(sale)

            product.quantity_in_stock -= item.quantity

            total += line_total

        bill.total_amount = total

        # Save the complete transaction.
        db.commit()
        db.refresh(bill)

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to create bill. Please try again."
        )

    # ----------------------------------------------
    # 4. Generate QR code and PDF receipt
    # ----------------------------------------------

    try:
        qr_path = generate_bill_qr(
            bill.id,
            customer.name,
            bill.total_amount,
            settings.STORE_NAME
        )

        bill.qr_code_path = qr_path

        pdf_path = generate_bill_pdf(
            bill,
            settings.STORE_NAME,
            qr_path
        )

        db.commit()
        db.refresh(bill)

    except Exception:
        db.rollback()

        # The bill and stock transaction have already
        # been committed. Do not silently delete them.
        raise HTTPException(
            status_code=500,
            detail=(
                "Bill was created, but receipt generation failed. "
                "Please contact the administrator."
            )
        )

    # ----------------------------------------------
    # 5. Send receipt email in background
    # ----------------------------------------------

    if customer.email:
        background_tasks.add_task(
            _email_in_background,
            bill.id,
            customer.email,
            customer.name,
            pdf_path
        )

    return bill
