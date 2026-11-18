
"""
Customer authentication routes.

Features:
- Customer registration
- Customer login using email or mobile
- Email OTP verification
- Mobile verification placeholder (SMS integration required)
- Forgot password
- Password reset
- JWT authentication
"""

import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, CustomerVerification, VerificationType
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
# Helpers
# --------------------------------------------------

def get_utc_now():
    """
    Return UTC time without timezone information.
    This matches SQLAlchemy DateTime columns that
    are stored without timezone information.
    """
    return datetime.utcnow()


def hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def generate_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def validate_password_length(password: str):
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password must not exceed 72 UTF-8 bytes."
        )


def create_verification(
    db: Session,
    customer: Customer,
    verification_type: VerificationType
):
    """
    Store only the hashed OTP.
    Supported types: email, mobile, password_reset.
    """

    code = generate_otp()

    if verification_type == VerificationType.password_reset:
        expires_minutes = settings.CUSTOMER_PASSWORD_RESET_EXPIRE_MINUTES
    else:
        expires_minutes = settings.CUSTOMER_VERIFICATION_EXPIRE_MINUTES

    verification = CustomerVerification(
        customer_id=customer.id,
        verification_type=verification_type,
        token_hash=hash_otp(code),
        expires_at=get_utc_now() + timedelta(minutes=expires_minutes),
        verified_at=None,
        attempts=0
    )

    db.add(verification)
    db.flush()

    return code


def get_latest_verification(
    db: Session,
    customer_id: int,
    verification_type: VerificationType
):
    return (
        db.query(CustomerVerification)
        .filter(
            CustomerVerification.customer_id == customer_id,
            CustomerVerification.verification_type == verification_type,
            CustomerVerification.verified_at.is_(None)
        )
        .order_by(CustomerVerification.id.desc())
        .first()
    )


def check_otp(verification: CustomerVerification, otp: str):
    """
    Validate expiry, attempts and OTP hash.
    Increments attempts for each submitted code.
    """

    if verification.expires_at <= get_utc_now():
        raise HTTPException(
            status_code=400,
            detail="OTP has expired."
        )

    if verification.attempts >= settings.CUSTOMER_VERIFICATION_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Maximum OTP attempts exceeded."
        )

    verification.attempts += 1

    if not secrets.compare_digest(
        verification.token_hash,
        hash_otp(otp)
    ):
        return False

    return True


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

        email_code = create_verification(
            db,
            customer,
            VerificationType.email
        )

        db.commit()
        db.refresh(customer)

    except Exception:
        db.rollback()
        raise

    # Send the email after saving the account.
    try:
        send_customer_verification_email(
            customer.email,
            customer.name,
            email_code
        )
    except Exception:
        # Do not expose OTP or email delivery errors to the client.
        # Add a resend-verification route for failed delivery.
        pass

    
    return CustomerRegistrationOut(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        mobile_number=customer.mobile_number,
        email_verified=customer.email_verified,
        mobile_verified=customer.mobile_verified,
        is_active=customer.is_active,
        created_at=customer.created_at,
        message="Registration completed. Email verification is pending."
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
    customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found."
        )

    if customer.email_verified:
        return {"message": "Email is already verified."}

    verification = get_latest_verification(
        db,
        customer_id,
        VerificationType.email
    )

    if not verification:
        raise HTTPException(
            status_code=400,
            detail="No active verification code found."
        )

    try:
        valid = check_otp(verification, otp)

        if not valid:
            db.commit()
            raise HTTPException(
                status_code=400,
                detail="Invalid OTP."
            )

        verification.verified_at = get_utc_now()
        customer.email_verified = True

        db.commit()

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise

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
    Mobile OTP verification is intentionally unavailable
    until a real SMS provider and OTP delivery flow exist.
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
    customer = db.query(Customer).filter(
        Customer.email == email.strip().lower()
    ).first()

    # Do not reveal whether an account exists.
    generic_message = (
        "If an eligible account exists, password reset instructions will be sent."
    )

    if not customer or not customer.is_active:
        return {"message": generic_message}

    try:
        code = create_verification(
            db,
            customer,
            VerificationType.password_reset
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    try:
        send_customer_verification_email(
            customer.email,
            customer.name,
            code
        )
    except Exception:
        pass

    return {"message": generic_message}


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
    if new_password != confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match."
        )

    validate_password_length(new_password)

    customer = db.query(Customer).filter(
        Customer.email == email.strip().lower()
    ).first()

    if not customer or not customer.is_active:
        raise HTTPException(
            status_code=400,
            detail="Invalid reset request."
        )

    verification = get_latest_verification(
        db,
        customer.id,
        VerificationType.password_reset
    )

    if not verification:
        raise HTTPException(
            status_code=400,
            detail="Invalid reset request."
        )

    try:
        valid = check_otp(verification, otp)

        if not valid:
            db.commit()
            raise HTTPException(
                status_code=400,
                detail="Invalid reset code."
            )

        verification.verified_at = get_utc_now()
        customer.hashed_password = hash_password(new_password)

        db.commit()

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise

    return {"message": "Password reset successfully."}
