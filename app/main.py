from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
import os

from app.core.limiter import limiter
from app.api.routes import auth, tts, chats
from app.db.init_db import init_db

app = FastAPI(title="EA-TTS Backend")

@app.on_event("startup")
def on_startup():
    init_db()
    # Create TTS media folder once at startup instead of per-request
    from app.services.tts_pipeline import MEDIA_FOLDER, generate_tts
    import app.services.emotion as emotion_service
    os.makedirs(MEDIA_FOLDER, exist_ok=True)
    
    # Warm up ML models (FastSpeech, HiFiGAN, Emotion Classifier) 
    # to prevent the first client request from timing out and throwing a 500 error.
    try:
        from app.db.session import SessionLocal
        print("Warming up ML models...")
        # Pre-load emotion classifier
        emotion_service.detect_emotion("Warm up")
        
        # Pre-load TTS pipeline
        db = SessionLocal()
        generate_tts(text="Warm up", user_id=None, db=db, background_tasks=None)
        db.close()
        print("ML models warmed up successfully.")
    except Exception as e:
        print(f"Warning: ML model warmup failed: {e}")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://daneena.vercel.app",
    "https://daneena-ea-tts.buzz"
]

if os.getenv("FRONTEND_URL"):
    origins.append(os.getenv("FRONTEND_URL").rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter


async def custom_rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again after 1 minute."},
    )


# app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)


app.include_router(auth.router)
app.include_router(tts.router)
app.include_router(chats.router)
