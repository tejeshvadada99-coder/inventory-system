"""
auth.py
-------
Everything related to "who is logged in and are they allowed to do this":

- hash_password / verify_password  -> passwords are never stored in plain text
- create_access_token              -> issues a signed JWT after successful login
- get_current_user                 -> reads the JWT from the request and loads the User
- require_admin / require_employee / require_customer -> route guards; use as a
  FastAPI dependency to block a whole endpoint unless the caller has that role
- get_optional_user                -> like get_current_user, but returns None for
  guests instead of an error (used by the public chatbot)

How the pieces connect: the browser logs in via /auth/login, receives a JWT,
and stores it. Every following request sends that JWT in the
"Authorization: Bearer <token>" header. FastAPI's Depends() system runs
get_current_user automatically before your route code executes.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User, RoleEnum

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_employee(current_user: User = Depends(get_current_user)) -> User:
    # Admins can also use employee tools; employees cannot use admin tools.
    if current_user.role not in (RoleEnum.employee, RoleEnum.admin):
        raise HTTPException(status_code=403, detail="Employee access required")
    return current_user


def require_customer(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != RoleEnum.customer:
        raise HTTPException(status_code=403, detail="Customer access required")
    return current_user


def get_optional_user(
    token: Optional[str] = Depends(oauth2_optional), db: Session = Depends(get_db)
) -> Optional[User]:
    """Logged-in user if a valid token was sent, otherwise None (a guest)."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
    user = db.query(User).filter(User.username == payload.get("sub")).first()
    return user if user and user.is_active else None
