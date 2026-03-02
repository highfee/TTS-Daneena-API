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
    from app.services.tts_pipeline import MEDIA_FOLDER
    os.makedirs(MEDIA_FOLDER, exist_ok=True)

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
