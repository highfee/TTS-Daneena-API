import uuid
from sqlalchemy import Column, Integer, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base

class AudioQualityMetric(Base):
    __tablename__ = "audio_quality_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tts_request_id = Column(UUID(as_uuid=True), ForeignKey("tts_requests.id"))
    mos_score = Column(Integer)
    intelligibility = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("mos_score BETWEEN 1 AND 5"),
        CheckConstraint("intelligibility BETWEEN 1 AND 5"),
    )
