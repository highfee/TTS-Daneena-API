import os
import time
import uuid
import functools
import soundfile as sf
from types import SimpleNamespace

from app.models.tts_request import TTSRequest
from app.services.emotion import detect_emotion
from app.services.prosody import get_prosody
from app.services.fastspeech import FastSpeech2Service
from app.services.hifigan import HiFiGANService

fastspeech = FastSpeech2Service()
hifigan = HiFiGANService()

MEDIA_FOLDER = "app/media/tts"

# ---------------------------------------------------------------------------
# Audio cache: avoids re-running the full ML pipeline for repeated inputs.
# Keyed on (text, emotion) -> numpy audio array.
# maxsize=64 means we keep the last 64 unique (text, emotion) results.
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=64)
def _synthesize_cached(text: str, emotion: str, speed: float, pitch_shift: float, energy_shift: float):
    """
    Pure inference function with no side effects — safe to cache.
    Returns the raw audio numpy array.
    """
    prosody = {
        "speed": speed,
        "pitch_shift": pitch_shift,
        "energy_shift": energy_shift,
    }
    mel = fastspeech.synthesize(text, prosody)
    audio = hifigan.vocode(mel)
    return audio


def _save_to_db(db, request_id, user_id, text, emotion, confidence, file_path, latency, chat_id):
    """Separated DB persistence logic — can be called as a BackgroundTask."""
    valid_chat_id = None
    if chat_id:
        try:
            valid_chat_id = uuid.UUID(str(chat_id))
        except (ValueError, AttributeError):
            valid_chat_id = None

    tts_request = TTSRequest(
        id=request_id,
        user_id=user_id,
        input_text=text,
        detected_emotion=emotion,
        confidence_score=confidence,
        audio_path=file_path,
        latency_ms=latency,
        chat_id=valid_chat_id,
    )
    db.add(tts_request)
    db.commit()
    db.refresh(tts_request)


def generate_tts(text: str, user_id, db, chat_id=None, background_tasks=None):

    start_time = time.time()

    # 1. Emotion Detection — cached via @lru_cache in emotion.py
    emotion, confidence = detect_emotion(text)

    # 2. Prosody Mapping
    prosody = get_prosody(emotion)

    # 3. Synthesize — cached via @lru_cache; skips full ML inference on repeat
    audio = _synthesize_cached(
        text=text,
        emotion=emotion,
        speed=prosody.get("speed", 1.0),
        pitch_shift=prosody.get("pitch_shift", 0.0),
        energy_shift=prosody.get("energy_shift", 0.0),
    )

    latency = int((time.time() - start_time) * 1000)

    # 4. Save audio file (makedirs is handled at app startup)
    request_id = uuid.uuid4()
    file_path = os.path.join(MEDIA_FOLDER, f"{request_id}.wav")
    sf.write(file_path, audio, 22050)

    if user_id:
        if background_tasks is not None:
            # Non-blocking: DB write happens after response is returned to client
            background_tasks.add_task(
                _save_to_db,
                db, request_id, user_id, text, emotion, confidence, file_path, latency, chat_id
            )
            # Return a lightweight object immediately (no DB round-trip)
            return SimpleNamespace(
                id=request_id,
                input_text=text,
                detected_emotion=emotion,
                confidence_score=confidence,
                audio_path=file_path,
                created_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                latency_ms=latency,
            )
        else:
            # Fallback: synchronous write (e.g. called from a context without BackgroundTasks)
            _save_to_db(db, request_id, user_id, text, emotion, confidence, file_path, latency, chat_id)
            # Re-query to get the full ORM object
            return db.query(TTSRequest).filter(TTSRequest.id == request_id).first()
    else:
        # Anonymous users: return lightweight object, no DB write
        return SimpleNamespace(
            id=request_id,
            input_text=text,
            detected_emotion=emotion,
            confidence_score=confidence,
            audio_path=file_path,
            created_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            latency_ms=latency,
        )