
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, Token
from app.auth import verify_password, create_access_token

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
