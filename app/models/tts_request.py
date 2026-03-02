import uuid
from sqlalchemy import Column, Text, String, Integer, DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class TTSRequest(Base):
    __tablename__ = "tts_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"))
    input_text = Column(Text, nullable=False)
    detected_emotion = Column(String(50))
    confidence_score = Column(Float)
    audio_path = Column(Text)
    latency_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chat = relationship("Chat", back_populates="messages")
