
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import User, Customer
from app.schemas import (
    LoginRequest,
    Token,
    CustomerRegister,
    CustomerLoginRequest,
    CustomerRegistrationOut,
)
from app.auth import (
    verify_password,
    hash_password,
    create_access_token,
    create_customer_access_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# --------------------------------------------------
# ADMIN / EMPLOYEE LOGIN
# --------------------------------------------------

@router.post("/login", response_model=Token)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.username == payload.username)
        .first()
    )

    if not user or not verify_password(
        payload.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled"
        )

    token = create_access_token(
        data={"sub": user.username}
    )

    return Token(
        access_token=token,
        role=user.role.value,
        full_name=user.full_name
    )


# --------------------------------------------------
# CUSTOMER REGISTRATION
# --------------------------------------------------

@router.post(
    "/customer/register",
    response_model=CustomerRegistrationOut,
    status_code=status.HTTP_201_CREATED
)
def customer_register(
    payload: CustomerRegister,
    db: Session = Depends(get_db)
):
    if payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )

    email = str(payload.email).strip().lower()
    mobile_number = payload.mobile_number.strip()

    existing_email = (
        db.query(Customer)
        .filter(func.lower(Customer.email) == email)
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists"
        )

    existing_mobile = (
        db.query(Customer)
        .filter(Customer.mobile_number == mobile_number)
        .first()
    )

    if existing_mobile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this mobile number already exists"
        )

    customer = Customer(
        name=payload.name.strip(),
        email=email,
        mobile_number=mobile_number,
        hashed_password=hash_password(payload.password),
        address=payload.address,
        is_active=True,
        email_verified=False,
        mobile_verified=False
    )

    try:
        db.add(customer)
        db.commit()
        db.refresh(customer)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create account. Please check your details."
        )

    return CustomerRegistrationOut(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        mobile_number=customer.mobile_number,
        message=(
            "Registration successful. "
            "Please complete email and mobile verification."
        )
    )


# --------------------------------------------------
# CUSTOMER LOGIN
# --------------------------------------------------

@router.post("/customer/login", response_model=Token)
def customer_login(
    payload: CustomerLoginRequest,
    db: Session = Depends(get_db)
):
    identifier = payload.identifier.strip()

    customer = (
        db.query(Customer)
        .filter(
            (
                func.lower(Customer.email) == identifier.lower()
            )
            | (
                Customer.mobile_number == identifier
            )
        )
        .first()
    )

    if not customer or not customer.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/mobile number or password"
        )

    if not verify_password(
        payload.password,
        customer.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/mobile number or password"
        )

    if not customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This customer account has been disabled"
        )

    if not customer.email_verified or not customer.mobile_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email and mobile number before logging in"
        )

    token = create_customer_access_token(customer.id)

    return Token(
        access_token=token,
        role="customer",
        full_name=customer.name
    )
