"""
routers/chatbot_routes.py
---------------------------
Public endpoint - guests can chat without logging in. If the browser also
sends a valid customer token, the reply becomes personal (points, orders,
members-only offers).

  POST /chat  { "message": "what are today's offers?" } -> { "reply": "..." }
"""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_optional_user
from app.database import get_db
from app.models import User
from app.schemas import ChatRequest, ChatResponse
from app.chatbot import get_bot_reply

router = APIRouter(tags=["chatbot"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    return ChatResponse(reply=get_bot_reply(payload.message, db, user))
