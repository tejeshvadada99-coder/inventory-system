
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ChatRequest, ChatResponse
from app.chatbot import get_bot_reply

router = APIRouter(tags=["chatbot"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    reply = get_bot_reply(payload.message, db)
    return ChatResponse(reply=reply)
