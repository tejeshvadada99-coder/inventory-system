
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ChatRequest, ChatResponse
from app.chatbot import get_bot_reply

from app.auth import get_current_customer
from app.models import Customer


router = APIRouter(tags=["chatbot"])


# ==================================================
# PUBLIC CHATBOT
# ==================================================

@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Public chatbot.
    Existing website chatbot functionality is preserved.
    """

    reply = get_bot_reply(
        payload.message,
        db
    )

    return ChatResponse(reply=reply)


# ==================================================
# AUTHENTICATED CUSTOMER CHATBOT
# ==================================================

@router.post(
    "/customer/chat",
    response_model=ChatResponse
)
def customer_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    """
    Customer-authenticated chatbot.

    The customer identity is obtained from the access token.
    """

    reply = get_bot_reply(
        payload.message,
        db
    )

    return ChatResponse(reply=reply)
