# import os
# import time
# import uuid
# import functools

# import numpy as np
# import soundfile as sf
# from types import SimpleNamespace

# import torch

# from app.models.tts_request import TTSRequest
# from app.services.emotion import detect_emotion
# from app.services.prosody import get_prosody
# from app.services.fastspeech import FastSpeech2Service
# from app.services.hifigan import HiFiGANService

# fastspeech = FastSpeech2Service()
# hifigan = HiFiGANService()

# MEDIA_FOLDER = "app/media/tts"


# # ---------------------------------------------------------------------------
# # Audio cache: avoids re-running the full ML pipeline for repeated inputs.
# # Keyed on (text, emotion) -> numpy audio array.
# # maxsize=64 means we keep the last 64 unique (text, emotion) results.
# # ---------------------------------------------------------------------------
# import threading
# _inference_lock = threading.Lock()

# @functools.lru_cache(maxsize=64)
# def _synthesize_cached(
#     text: str, emotion: str, speed: float, pitch_shift: float, energy_shift: float
# ):
#     """
#     Pure inference function with no side effects — safe to cache.
#     Returns the raw audio numpy array (float32, 1-D).

#     fastspeech.synthesize() contract:
#       - VITS fallback  → 1-D numpy float32 array  (wav, ready to save)
#       - Local FS2+GST  → 2-D torch tensor (T, n_mels) (mel, needs HiFiGAN)
#     """
#     prosody = {
#         "speed": speed,
#         "pitch_shift": pitch_shift,
#         "energy_shift": energy_shift,
#     }
#     with _inference_lock:
#         result = fastspeech.synthesize(text, prosody, emotion=emotion)

#         # --- Convert to numpy if still a tensor ---
#         if hasattr(result, "cpu"):
#             result = result.cpu().numpy()
#         result = np.asarray(result, dtype=np.float32)

#         # --- Route on dimensionality ---
#         if result.ndim == 1:
#             # Already a waveform (VITS / built-in vocoder)
#             audio = result
#         elif result.ndim == 2:
#             # Mel-spectrogram (T, n_mels) — run through HiFiGAN
#             mel_tensor = torch.from_numpy(result)
#             audio = hifigan.vocode(mel_tensor)
#             audio = np.asarray(audio, dtype=np.float32)
#         else:
#             raise RuntimeError(f"[TTS] Unexpected result shape from synthesize(): {result.shape}")

#     # Normalise: prevent digital clipping, ensure audible amplitude
#     max_val = np.abs(audio).max()
#     if max_val > 0:
#         audio = audio / max_val * 0.95

#     print(f"[TTS] Final audio: shape={audio.shape} min={audio.min():.3f} max={audio.max():.3f}")
#     return audio


# def _save_to_db(
#     db, request_id, user_id, text, emotion, confidence, file_path, latency, chat_id
# ):
#     """Separated DB persistence logic — can be called as a BackgroundTask."""
#     valid_chat_id = None
#     if chat_id:
#         try:
#             valid_chat_id = uuid.UUID(str(chat_id))
#         except (ValueError, AttributeError):
#             valid_chat_id = None

#     tts_request = TTSRequest(
#         id=request_id,
#         user_id=user_id,
#         input_text=text,
#         detected_emotion=emotion,
#         confidence_score=confidence,
#         audio_path=file_path,
#         latency_ms=latency,
#         chat_id=valid_chat_id,
#     )
#     db.add(tts_request)
#     db.commit()
#     db.refresh(tts_request)


# def generate_tts(text: str, user_id, db, chat_id=None, background_tasks=None):

#     start_time = time.time()

#     # 1. Emotion Detection — cached via @lru_cache in emotion.py
#     emotion, confidence = detect_emotion(text)

#     # 2. Prosody Mapping
#     prosody = get_prosody(emotion)

#     # 3. Synthesize — cached via @lru_cache; skips full ML inference on repeat
#     audio = _synthesize_cached(
#         text=text,
#         emotion=emotion,
#         speed=prosody.get("speed", 1.0),
#         pitch_shift=prosody.get("pitch_shift", 0.0),
#         energy_shift=prosody.get("energy_shift", 0.0),
#     )

#     latency = int((time.time() - start_time) * 1000)

#     # 4. Save audio file (makedirs is handled at app startup)
#     request_id = uuid.uuid4()
#     file_path = os.path.join(MEDIA_FOLDER, f"{request_id}.wav")
#     sf.write(file_path, audio, 22050)

#     if user_id:
#         if background_tasks is not None:
#             # Non-blocking: DB write happens after response is returned to client
#             background_tasks.add_task(
#                 _save_to_db,
#                 db,
#                 request_id,
#                 user_id,
#                 text,
#                 emotion,
#                 confidence,
#                 file_path,
#                 latency,
#                 chat_id,
#             )
#             # Return a lightweight object immediately (no DB round-trip)
#             return SimpleNamespace(
#                 id=request_id,
#                 input_text=text,
#                 detected_emotion=emotion,
#                 confidence_score=confidence,
#                 audio_path=file_path,
#                 created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
#                 latency_ms=latency,
#             )
#         else:
#             # Fallback: synchronous write (e.g. called from a context without BackgroundTasks)
#             _save_to_db(
#                 db,
#                 request_id,
#                 user_id,
#                 text,
#                 emotion,
#                 confidence,
#                 file_path,
#                 latency,
#                 chat_id,
#             )
#             # Re-query to get the full ORM object
#             return db.query(TTSRequest).filter(TTSRequest.id == request_id).first()
#     else:
#         # Anonymous users: return lightweight object, no DB write
#         return SimpleNamespace(
#             id=request_id,
#             input_text=text,
#             detected_emotion=emotion,
#             confidence_score=confidence,
#             audio_path=file_path,
#             created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
#             latency_ms=latency,
#         )





import os
import time
import uuid
import functools
import threading

import numpy as np
import soundfile as sf
import torch
from types import SimpleNamespace

from app.models.tts_request import TTSRequest
from app.services.emotion import detect_emotion
from app.services.prosody import get_prosody
from app.services.fastspeech import FastSpeech2Service
# from app.services.emotion_postprocess import postprocess

# ── Service singletons ────────────────────────────────────────────────────────
fastspeech = FastSpeech2Service()

MEDIA_FOLDER = "app/media/tts"

# ── Inference lock & cache ────────────────────────────────────────────────────
_inference_lock = threading.Lock()


# @functools.lru_cache(maxsize=64)
# def _synthesize_cached(
#     text: str,
#     emotion: str,
#     speed: float,
#     pitch_shift: float,
#     energy_shift: float,
# ):
#     """
#     Pure inference function — safe to cache.
#     Returns a normalised 1-D float32 numpy audio array.

#     Pipeline:
#       Text → FastSpeech2 (pretrained) → wav → emotion post-processing → audio
#     """
#     prosody = {
#         "speed":        speed,
#         "pitch_shift":  pitch_shift,
#         "energy_shift": energy_shift,
#     }

#     with _inference_lock:
#         result = fastspeech.synthesize(text, prosody, emotion=emotion)

#     # ── Ensure numpy float32 ──────────────────────────────────────────────────
#     if hasattr(result, "cpu"):
#         result = result.cpu().numpy()
#     result = np.asarray(result, dtype=np.float32)

#     # ── Route on dimensionality ───────────────────────────────────────────────
#     if result.ndim == 1:
#         # Pretrained model returns wav directly — no HiFiGAN needed
#         audio = result
#     elif result.ndim == 2:
#         # Mel spectrogram fallback — should not happen with pretrained model
#         # but kept as a safety net in case vocoder tag changes
#         raise RuntimeError(
#             "[TTS] Received mel spectrogram from pretrained model — "
#             "check that vocoder_tag is set in FastSpeech2Service."
#         )
#     else:
#         raise RuntimeError(
#             f"[TTS] Unexpected result shape from synthesize(): {result.shape}"
#         )

#     # ── Emotion post-processing ───────────────────────────────────────────────
#     # Applies tempo, pitch shift, loudness, and EQ shaping per emotion.
#     # This is what differentiates Angry/Happy/Sad/Surprise/Neutral output.
#     audio = postprocess(audio, sr=22050, emotion=emotion)

#     # ── Normalise ─────────────────────────────────────────────────────────────
#     max_val = np.abs(audio).max()
#     if max_val > 0:
#         audio = audio / max_val * 0.95

#     print(
#         f"[TTS] Final audio: shape={audio.shape} "
#         f"min={audio.min():.3f} max={audio.max():.3f} "
#         f"emotion={emotion}"
#     )
#     return audio


@functools.lru_cache(maxsize=64)
def _synthesize_cached(
    text: str,
    emotion: str,
    speed: float,
    pitch_shift: float,
    energy_shift: float,
):
    prosody = {
        "speed":        speed,
        "pitch_shift":  pitch_shift,
        "energy_shift": energy_shift,
    }

    with _inference_lock:
        result = fastspeech.synthesize(text, prosody, emotion=emotion)

    if hasattr(result, "cpu"):
        result = result.cpu().numpy()
    audio = np.asarray(result, dtype=np.float32)

    # Normalize
    max_val = np.abs(audio).max()
    if max_val > 0:
        audio = audio / max_val * 0.95

    print(f"[TTS] Final audio: shape={audio.shape} emotion={emotion}")
    return audio

# ── DB persistence ────────────────────────────────────────────────────────────
def _save_to_db(
    db, request_id, user_id, text, emotion, confidence, file_path, latency, chat_id
):
    """Separated DB persistence — safe to call as a BackgroundTask."""
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


# ── Main entry point ──────────────────────────────────────────────────────────
def generate_tts(
    text: str,
    user_id,
    db,
    chat_id=None,
    background_tasks=None,
):
    start_time = time.time()

    # 1. Emotion detection
    emotion, confidence = detect_emotion(text)

    # 2. Prosody mapping
    prosody = get_prosody(emotion)

    # 3. Synthesize + post-process (cached)
    audio = _synthesize_cached(
        text=text,
        emotion=emotion,
        speed=prosody.get("speed", 1.0),
        pitch_shift=prosody.get("pitch_shift", 0.0),
        energy_shift=prosody.get("energy_shift", 0.0),
    )

    latency = int((time.time() - start_time) * 1000)

    # 4. Save audio file
    request_id = uuid.uuid4()
    file_path = os.path.join(MEDIA_FOLDER, f"{request_id}.wav")
    os.makedirs(MEDIA_FOLDER, exist_ok=True)
    # sf.write(file_path, audio, 22050)
    sf.write(file_path, audio, 24000)  # ← was 22050

    # 5. Persist to DB
    if user_id:
        if background_tasks is not None:
            background_tasks.add_task(
                _save_to_db,
                db,
                request_id,
                user_id,
                text,
                emotion,
                confidence,
                file_path,
                latency,
                chat_id,
            )
            return SimpleNamespace(
                id=request_id,
                input_text=text,
                detected_emotion=emotion,
                confidence_score=confidence,
                audio_path=file_path,
                created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                latency_ms=latency,
            )
        else:
            _save_to_db(
                db,
                request_id,
                user_id,
                text,
                emotion,
                confidence,
                file_path,
                latency,
                chat_id,
            )
            return db.query(TTSRequest).filter(TTSRequest.id == request_id).first()
    else:
        # Anonymous — no DB write
        return SimpleNamespace(
            id=request_id,
            input_text=text,
            detected_emotion=emotion,
            confidence_score=confidence,
            audio_path=file_path,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            latency_ms=latency,
        )