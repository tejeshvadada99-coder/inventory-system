"""
routers/auth_routes.py
-----------------------
  POST /auth/login     -> everyone signs in here (admin, employee, customer).
                          Staff use their username. Customers can use their
                          email OR mobile number. The response includes the
                          `role`, which the homepage JS uses to pick the dashboard.
  POST /auth/register  -> customer self-registration. No email/OTP verification
                          (by design - keeps it simple on the free Render plan),
                          so the account is created and logged in immediately.

Safety rule for registration: if the mobile number already belongs to a
customer that staff billed earlier, the new account is linked to that
record (so old bills and points show up) ONLY when the email matches the
one saved at billing. Otherwise registration is refused, because without
OTP we can't prove the person owns that number - and linking by mobile
alone would let a stranger read someone else's purchase history.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Customer, RoleEnum
from app.schemas import LoginRequest, Token, CustomerRegister
from app.auth import verify_password, hash_password, create_access_token
from app.utils.customer_helpers import normalize_mobile, find_customer_by_mobile, points_for_amount

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    ident = payload.username.strip()

    # Match on username or email (case-insensitive for email)...
    user = db.query(User).filter(
        or_(User.username == ident, func.lower(User.email) == ident.lower())
    ).first()

    # ...or, for customers, on the mobile number saved on their customer record.
    if not user:
        customer = find_customer_by_mobile(db, ident)
        if customer and customer.user:
            user = customer.user

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect login details or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been disabled")

    token = create_access_token(data={"sub": user.username})
    return Token(access_token=token, role=user.role.value, full_name=user.full_name)


@router.post("/register", response_model=Token)
def register_customer(payload: CustomerRegister, db: Session = Depends(get_db)):
    name = payload.full_name.strip()
    email = payload.email.strip().lower()
    mobile = normalize_mobile(payload.mobile_number)
    digits = mobile.lstrip("+")

    if len(name) < 2:
        raise HTTPException(400, "Please enter your full name")
    if not (7 <= len(digits) <= 15):
        raise HTTPException(400, "Please enter a valid mobile number (7-15 digits)")
    if len(payload.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if payload.password != payload.confirm_password:
        raise HTTPException(400, "Passwords do not match")

    if db.query(User).filter(or_(User.username == email, func.lower(User.email) == email)).first():
        raise HTTPException(400, "An account with this email already exists - please sign in")

    customer = find_customer_by_mobile(db, mobile)
    if customer and (
        customer.user_id is not None
        or not customer.email
        or customer.email.strip().lower() != email
    ):
        # Deliberately vague: doesn't reveal whether the number is known to the store.
        raise HTTPException(
            400,
            "We couldn't use this mobile number for a new account. If you already registered, "
            "please sign in. If you've shopped with us before, register with the same email you "
            "gave at billing, or ask our staff to update it.",
        )

    user = User(
        full_name=name,
        username=email,          # customers sign in with their email
        email=email,
        hashed_password=hash_password(payload.password),
        role=RoleEnum.customer,
    )
    db.add(user)
    db.flush()

    if customer:
        # Existing billing record with a matching email -> link it and credit past purchases.
        customer.user_id = user.id
        customer.loyalty_points = points_for_amount(sum(b.total_amount for b in customer.bills))
    else:
        db.add(Customer(name=name, mobile_number=mobile, email=email, user_id=user.id))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "That email or mobile number is already registered")

    token = create_access_token(data={"sub": user.username})
    return Token(access_token=token, role=user.role.value, full_name=user.full_name)
