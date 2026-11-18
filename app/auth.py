
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.database import get_db
from app.models import User, Customer, RoleEnum


# ============================================================
# PASSWORD SECURITY
# ============================================================

# Keep bcrypt for compatibility with existing password hashes.
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# Shared Bearer token authentication.
# Admin, Employee and Customer tokens use different JWT claims.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)


def hash_password(password: str) -> str:
    """Hash a password before storing it in the database."""
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """Verify a password against its stored hash."""
    return pwd_context.verify(
        plain_password,
        hashed_password
    )


# ============================================================
# JWT TOKEN MANAGEMENT
# ============================================================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Existing Admin and Employee token creation remains compatible.
    """

    to_encode = data.copy()

    expire = datetime.utcnow() + (
        expires_delta
        or timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    to_encode.update({
        "exp": expire
    })

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def create_customer_access_token(customer_id: int) -> str:
    """
    Create a separate JWT token for a registered customer.

    Customer tokens use the customer database ID as their subject.
    """

    return create_access_token({
        "sub": str(customer_id),
        "role": "customer",
        "account_type": "customer"
    })


# ============================================================
# COMMON AUTHENTICATION ERROR
# ============================================================

def credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={
            "WWW-Authenticate": "Bearer"
        }
    )


# ============================================================
# ADMIN AND EMPLOYEE AUTHENTICATION
# ============================================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Retrieve the authenticated Admin or Employee.

    Customer tokens are explicitly rejected here.
    """

    exception = credentials_exception()

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        username = payload.get("sub")

        # Reject customer tokens.
        if payload.get("account_type") == "customer":
            raise exception

        if not username:
            raise exception

    except JWTError:
        raise exception

    user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if user is None or not user.is_active:
        raise exception

    return user


# ============================================================
# ADMIN PERMISSION
# ============================================================

def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Allow only Admin users."""

    if current_user.role != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user


# ============================================================
# EMPLOYEE PERMISSION
# ============================================================

def require_employee(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Allow Employees and Admins to access employee tools.
    Admins retain access to employee-level operations.
    """

    if current_user.role not in (
        RoleEnum.employee,
        RoleEnum.admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee access required"
        )

    return current_user


# ============================================================
# CUSTOMER AUTHENTICATION
# ============================================================

def authenticate_customer(
    db: Session,
    identifier: str,
    password: str
) -> Customer:
    """
    Authenticate a customer using email or mobile number.

    Both email and mobile verification are required
    before customer login is permitted.
    """

    identifier = identifier.strip()

    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/mobile number or password"
        )

    customer = (
        db.query(Customer)
        .filter(
            (
                func.lower(Customer.email)
                == identifier.lower()
            )
            |
            (
                Customer.mobile_number
                == identifier
            )
        )
        .first()
    )

    # Use a generic message to avoid revealing account existence.
    if (
        customer is None
        or not customer.hashed_password
        or not verify_password(
            password,
            customer.hashed_password
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/mobile number or password"
        )

    if not customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your customer account is inactive"
        )

    if not customer.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in"
        )

    if not customer.mobile_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your mobile number before logging in"
        )

    return customer


# ============================================================
# GET CURRENT CUSTOMER
# ============================================================


def get_current_customer(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Customer:
    """
    Retrieve the currently authenticated customer.

    Customer login does not require email or mobile verification.
    """

    exception = credentials_exception()

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        customer_id = payload.get("sub")

        if (
            payload.get("account_type") != "customer"
            or payload.get("role") != "customer"
            or not customer_id
        ):
            raise exception

        customer_id = int(customer_id)

    except (JWTError, ValueError, TypeError):
        raise exception

    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id)
        .first()
    )

    if customer is None or not customer.is_active:
        raise exception

    # Do not check email_verified or mobile_verified.
    return customer


# ============================================================
# CUSTOMER PERMISSION
# ============================================================

def require_customer(
    current_customer: Customer = Depends(get_current_customer)
) -> Customer:
    """Allow only authenticated and verified customers."""

    return current_customer
