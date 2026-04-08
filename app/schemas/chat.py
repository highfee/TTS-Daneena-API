from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List, Optional

class ChatBase(BaseModel):
    title: str

class ChatCreate(ChatBase):
    pass

class ChatUpdate(BaseModel):
    title: Optional[str] = None

class TTSRequestResponse(BaseModel):
    id: UUID
    input_text: str
    detected_emotion: Optional[str] = None
    confidence_score: Optional[float] = None
    audio_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChatResponse(ChatBase):
    id: UUID
    user_id: Optional[UUID]
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[TTSRequestResponse] = []

    class Config:
        from_attributes = True
