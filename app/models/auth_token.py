import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    user = relationship("User", back_populates="auth_tokens")
