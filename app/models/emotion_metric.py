import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class EmotionMetric(Base):
    __tablename__ = "emotion_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tts_request_id = Column(UUID(as_uuid=True), ForeignKey("tts_requests.id"))
    predicted_emotion = Column(String(50))
    actual_emotion = Column(String(50))
    is_correct = Column(Boolean)
