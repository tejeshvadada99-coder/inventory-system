
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer
from app.schemas import (
    CustomerRegister,
    CustomerLoginRequest,
    CustomerRegistrationOut,
    Token,
)
from app.auth import (
    hash_password,
    verify_password,
    create_customer_access_token,
)


router = APIRouter(
    prefix="/auth/customer",
    tags=["Customer Authentication"]
)


# --------------------------------------------------
# Password validation
# --------------------------------------------------

def validate_password_length(password: str):
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password must not exceed 72 UTF-8 bytes."
        )


# --------------------------------------------------
# Customer registration
# --------------------------------------------------

@router.post(
    "/register",
    response_model=CustomerRegistrationOut,
    status_code=status.HTTP_201_CREATED
)
def register_customer(
    payload: CustomerRegister,
    db: Session = Depends(get_db)
):
    if payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match."
        )

    validate_password_length(payload.password)

    email = payload.email.strip().lower()
    mobile = payload.mobile_number.strip()

    # Check whether email or mobile already exists
    existing_customer = db.query(Customer).filter(
        or_(
            Customer.email == email,
            Customer.mobile_number == mobile
        )
    ).first()

    if existing_customer:
        raise HTTPException(
            status_code=409,
            detail="An account with this email or mobile number already exists."
        )

    # Create customer account immediately
    customer = Customer(
        name=payload.name.strip(),
        email=email,
        mobile_number=mobile,
        address=payload.address,
        hashed_password=hash_password(payload.password),
        is_active=True,

        # Verification is not required for registration or login.
        email_verified=False,
        mobile_verified=False,

        loyalty_points=0
    )

    try:
        db.add(customer)
        db.commit()
        db.refresh(customer)

    except Exception:
        db.rollback()
        raise

    return CustomerRegistrationOut(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        mobile_number=customer.mobile_number,
        email_verified=customer.email_verified,
        mobile_verified=customer.mobile_verified,
        is_active=customer.is_active,
        created_at=customer.created_at,
        message="Account created successfully. You can now log in."
    )


# --------------------------------------------------
# Customer login
# --------------------------------------------------

@router.post("/login", response_model=Token)
def customer_login(
    payload: CustomerLoginRequest,
    db: Session = Depends(get_db)
):
    identifier = payload.identifier.strip()

    # Login using either email or mobile number
    customer = db.query(Customer).filter(
        or_(
            Customer.email == identifier.lower(),
            Customer.mobile_number == identifier
        )
    ).first()

    if not customer or not customer.hashed_password:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email/mobile number or password."
        )

    if not verify_password(
        payload.password,
        customer.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email/mobile number or password."
        )

    if not customer.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account has been disabled."
        )

    # No email or mobile verification required
    token = create_customer_access_token(customer.id)

    return Token(
        access_token=token,
        role="customer",
        full_name=customer.name
    )
