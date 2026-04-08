from app.db.base import Base
from app.db.session import engine



# I import models so Alembic sees them
from app.models.user import User
from app.models.tts_request import TTSRequest
from app.models.emotion_metric import EmotionMetric
from app.models.audio_quality_metric import AudioQualityMetric
from app.models.auth_token import AuthToken
from app.models.refresh_token import RefreshToken
from app.models.chat import Chat


def init_db():
    Base.metadata.create_all(bind=engine)
