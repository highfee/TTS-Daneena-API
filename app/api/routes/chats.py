from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
from typing import List, Optional

from app.db.session import get_db
from app.models.chat import Chat
from app.models.tts_request import TTSRequest
from app.schemas.chat import ChatCreate, ChatResponse, ChatUpdate
from app.api.routes.deps import get_current_user_id, get_optional_user_id

router = APIRouter(prefix="/chats", tags=["Chats"])

@router.post("", response_model=ChatResponse)
def create_chat(
    payload: ChatCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    chat = Chat(user_id=user_id, title=payload.title)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat

@router.get("", response_model=List[ChatResponse])
def get_chats(
    db: Session = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_optional_user_id)
):
    if not user_id:
        return []
    return db.query(Chat).options(joinedload(Chat.messages)).filter(Chat.user_id == user_id).order_by(Chat.updated_at.desc()).all()

@router.get("/{chat_id}", response_model=ChatResponse)
def get_chat(
    chat_id: UUID,
    db: Session = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_optional_user_id)
):
    if not user_id:
        raise HTTPException(status_code=404, detail="Chat not found")
        
    chat = db.query(Chat).options(joinedload(Chat.messages)).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.delete("/{chat_id}")
def delete_chat(
    chat_id: UUID,
    db: Session = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_optional_user_id)
):
    if not user_id:
        raise HTTPException(status_code=404, detail="Chat not found")
        
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    db.delete(chat)
    db.commit()
    return {"message": "Chat deleted"}
