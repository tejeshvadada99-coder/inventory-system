
"""
app/routers/customer_auth.py
----------------------------
Customer authentication routes.

Features:
- Customer registration
- Customer login using email or mobile
- Email OTP verification
- Mobile OTP verification (SMS provider integration required)
- Forgot password
- Password reset
- JWT authentication

Existing admin and employee authentication remains in auth_routes.py.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, CustomerVerification
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
from app.config import settings
from app.utils.email_sender import send_customer_verification_email


router = APIRouter(
    prefix="/auth/customer",
    tags=["Customer Authentication"]
)


# --------------------------------------------------
# Configuration helpers
# --------------------------------------------------

def get_utc_now():
    return datetime.now(timezone.utc)


def hash_otp(code: str) -> str:
    """
    Hash an OTP before storing it in the database.
    """

    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def generate_otp() -> str:
    """
    Generate a cryptographically secure six-digit OTP.
    """

    return f"{secrets.randbelow(1000000):06d}"


def validate_password_length(password: str):
    """
    bcrypt supports passwords up to 72 UTF-8 bytes.
    """

    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password must not exceed 72 UTF-8 bytes."
        )


def create_verification(
    db: Session,
    customer: Customer,
    verification_type: str
):
    """
    Create and store a hashed OTP.

    verification_type:
        email
        mobile
        password_reset
    """

    code = generate_otp()

    expires_minutes = (
        settings.CUSTOMER_PASSWORD_RESET_EXPIRE_MINUTES
        if verification_type == "password_reset"
        else settings.CUSTOMER_VERIFICATION_EXPIRE_MINUTES
    )

    verification = CustomerVerification(
        customer_id=customer.id,
        verification_type=verification_type,
        code_hash=hash_otp(code),
        expires_at=get_utc_now() + timedelta(minutes=expires_minutes),
        attempts=0,
        is_used=False
    )

    db.add(verification)
    db.flush()

    return code


# --------------------------------------------------
# Registration
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
    """
    Register a new customer.

    Both email and mobile verification are required
    before customer login is allowed.
    """

    if payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match."
        )

    validate_password_length(payload.password)

    email = payload.email.strip().lower()
    mobile = payload.mobile_number.strip()

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

    customer = Customer(
        name=payload.name.strip(),
        email=email,
        mobile_number=mobile,
        address=payload.address,
        hashed_password=hash_password(payload.password),
        is_active=True,
        email_verified=False,
        mobile_verified=False,
        loyalty_points=0
    )

    try:
        db.add(customer)
        db.flush()

        # Generate email OTP.
        email_code = create_verification(
            db,
            customer,
            "email"
        )

        db.commit()
        db.refresh(customer)

    except Exception:
        db.rollback()
        raise

    # Send email after the database transaction commits.
    try:
        send_customer_verification_email(
            email,
            customer.name,
            email_code
        )
    except Exception:
        # Account is created, but email delivery failed.
        # A resend-verification endpoint will be needed.
        pass

    return CustomerRegistrationOut(
        message="Registration completed. Email verification is pending.",
        customer_id=customer.id,
        email=customer.email,
        mobile_number=customer.mobile_number
    )


# --------------------------------------------------
# Customer login
# --------------------------------------------------

@router.post("/login", response_model=Token)
def customer_login(
    payload: CustomerLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login using registered email or mobile number.
    """

    identifier = payload.identifier.strip()

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

    if not customer.email_verified or not customer.mobile_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify both your email and mobile number before logging in."
        )

    token = create_customer_access_token(customer.id)

    return Token(
        access_token=token,
        role="customer",
        full_name=customer.name
    )


# --------------------------------------------------
# Email verification
# --------------------------------------------------

@router.post("/verify-email")
def verify_customer_email(
    customer_id: int,
    otp: str,
    db: Session = Depends(get_db)
):
    """
    Verify the customer's email using OTP.
    """

    customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    if customer.email_verified:
        return {"message": "Email is already verified."}

    verification = db.query(CustomerVerification).filter(
        CustomerVerification.customer_id == customer_id,
        CustomerVerification.verification_type == "email",
        CustomerVerification.is_used == False
    ).order_by(
        CustomerVerification.id.desc()
    ).first()

    if not verification:
        raise HTTPException(status_code=400, detail="No active verification code found.")

    if verification.expires_at <= get_utc_now():
        raise HTTPException(status_code=400, detail="OTP has expired.")

    if verification.attempts >= settings.CUSTOMER_VERIFICATION_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Maximum OTP attempts exceeded.")

    verification.attempts += 1

    if not secrets.compare_digest(
        verification.code_hash,
        hash_otp(otp)
    ):
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid OTP.")

    verification.is_used = True
    customer.email_verified = True

    db.commit()

    return {"message": "Email verified successfully."}


# --------------------------------------------------
# Mobile verification
# --------------------------------------------------

@router.post("/verify-mobile")
def verify_customer_mobile(
    customer_id: int,
    otp: str,
    db: Session = Depends(get_db)
):
    """
    Verify mobile OTP.

    This endpoint must only be enabled after a real SMS
    provider is connected and OTP delivery is implemented.
    """

    raise HTTPException(
        status_code=501,
        detail="Mobile OTP verification is not available yet. SMS provider integration is required."
    )


# --------------------------------------------------
# Forgot password
# --------------------------------------------------

@router.post("/forgot-password")
def forgot_customer_password(
    email: str,
    db: Session = Depends(get_db)
):
    """
    Request a password reset OTP through registered email.
    """

    customer = db.query(Customer).filter(
        Customer.email == email.strip().lower()
    ).first()

    # Avoid revealing whether an account exists.
    if not customer or not customer.is_active:
        return {
            "message": "If an eligible account exists, password reset instructions will be sent."
        }

    code = create_verification(
        db,
        customer,
        "password_reset"
    )

    db.commit()

    try:
        send_customer_verification_email(
            customer.email,
            customer.name,
            code
        )
    except Exception:
        # Do not expose account details or OTP in the response.
        pass

    return {
        "message": "If an eligible account exists, password reset instructions will be sent."
    }


# --------------------------------------------------
# Reset password
# --------------------------------------------------

@router.post("/reset-password")
def reset_customer_password(
    email: str,
    otp: str,
    new_password: str,
    confirm_password: str,
    db: Session = Depends(get_db)
):
    """
    Reset password using email OTP.
    """

    if new_password != confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match."
        )

    validate_password_length(new_password)

    customer = db.query(Customer).filter(
        Customer.email == email.strip().lower()
    ).first()

    if not customer:
        raise HTTPException(status_code=400, detail="Invalid reset request.")

    verification = db.query(CustomerVerification).filter(
        CustomerVerification.customer_id == customer.id,
        CustomerVerification.verification_type == "password_reset",
        CustomerVerification.is_used == False
    ).order_by(
        CustomerVerification.id.desc()
    ).first()

    if not verification:
        raise HTTPException(status_code=400, detail="Invalid reset request.")

    if verification.expires_at <= get_utc_now():
        raise HTTPException(status_code=400, detail="Reset code has expired.")

    if verification.attempts >= settings.CUSTOMER_VERIFICATION_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Maximum attempts exceeded.")

    verification.attempts += 1

    if not secrets.compare_digest(
        verification.code_hash,
        hash_otp(otp)
    ):
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid reset code.")

    verification.is_used = True
    customer.hashed_password = hash_password(new_password)

    db.commit()

    return {"message": "Password reset successfully."}
