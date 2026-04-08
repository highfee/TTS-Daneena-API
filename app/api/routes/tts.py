from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi.responses import FileResponse
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional, List

from app.db.session import get_db
from app.schemas.tts_schema import TTSCreate
from app.schemas.metrics_schema import PerformanceMetrics, LatencyPoint, EmotionCount, AudioQualityStats, FeedbackCreate
from app.services.tts_pipeline import generate_tts, MEDIA_FOLDER
from app.api.routes.deps import get_current_user_id, get_optional_user_id
from app.core.limiter import limiter
from app.models.user import User
import os

router = APIRouter(prefix="/tts", tags=["TTS"])

@router.post("/generate")
@limiter.limit("20/minute")
def generate_tts_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    payload: TTSCreate,
    db: Session = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_optional_user_id),
):

    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    tts_request = generate_tts(
        text=payload.text,
        user_id=user_id,
        chat_id=payload.chat_id,
        db=db,
        background_tasks=background_tasks,
    )

    return {
        "id": str(tts_request.id),
        "input_text": tts_request.input_text,
        "emotion": tts_request.detected_emotion,
        "confidence": round(tts_request.confidence_score, 4),
        "audio_url": str(request.url_for("get_audio", request_id=tts_request.id)),
        "created_at": tts_request.created_at
    }

@router.get("/audio/{request_id}", name="get_audio")
def get_audio(
    request_id: UUID,
    db: Session = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_optional_user_id),
):
    from app.models.tts_request import TTSRequest
    
    # Try to find in DB for authenticated users
    if user_id:
        tts_request = db.query(TTSRequest).filter(
            TTSRequest.id == request_id, 
            TTSRequest.user_id == user_id
        ).first()
        if tts_request:
            return FileResponse(
                path=tts_request.audio_path,
                media_type="audio/wav",
                filename=f"speech_{request_id}.wav",
            )

    # Fallback/Anonymous: Check disk directly
    # This acts as a 'temporary secret link' for anonymous users
    file_path = os.path.join(MEDIA_FOLDER, f"{request_id}.wav")
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path,
            media_type="audio/wav",
            filename=f"speech_{request_id}.wav",
        )

    raise HTTPException(status_code=404, detail="Audio not found")

@router.get("/metrics", response_model=PerformanceMetrics)
def get_metrics(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    from app.models.tts_request import TTSRequest
    from app.models.audio_quality_metric import AudioQualityMetric

    # 1. Basic Latency Stats
    stats = db.query(
        func.avg(TTSRequest.latency_ms).label("avg"),
        func.min(TTSRequest.latency_ms).label("min"),
        func.max(TTSRequest.latency_ms).label("max")
    ).filter(TTSRequest.user_id == user_id).one()

    # 2. Latency Trend (Last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    trend_query = db.query(
        func.date(TTSRequest.created_at).label("day"),
        func.avg(TTSRequest.latency_ms)
    ).filter(
        TTSRequest.user_id == user_id,
        TTSRequest.created_at >= seven_days_ago
    ).group_by(func.date(TTSRequest.created_at)).order_by(func.date(TTSRequest.created_at)).all()

    latency_trend = [
        LatencyPoint(date=str(row[0]), avg_latency=float(row[1])) 
        for row in trend_query
    ]

    # 3. Emotion Distribution
    emotion_query = db.query(
        TTSRequest.detected_emotion,
        func.count(TTSRequest.id)
    ).filter(TTSRequest.user_id == user_id).group_by(TTSRequest.detected_emotion).all()

    emotion_distribution = [
        EmotionCount(emotion=row[0] or "unknown", count=row[1]) 
        for row in emotion_query
    ]

    # 4. Audio Quality stats
    quality_stats = db.query(
        func.avg(AudioQualityMetric.mos_score),
        func.avg(AudioQualityMetric.intelligibility)
    ).join(TTSRequest).filter(TTSRequest.user_id == user_id).one()

    return PerformanceMetrics(
        avg_latency=float(stats.avg or 0),
        min_latency=int(stats.min or 0),
        max_latency=int(stats.max or 0),
        latency_trend=latency_trend,
        emotion_distribution=emotion_distribution,
        audio_quality=AudioQualityStats(
            avg_mos=float(quality_stats[0]) if quality_stats[0] else None,
            avg_intelligibility=float(quality_stats[1]) if quality_stats[1] else None
        )
    )

@router.post("/feedback/{request_id}")
def submit_feedback(
    request_id: UUID,
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    from app.models.tts_request import TTSRequest
    from app.models.audio_quality_metric import AudioQualityMetric

    # Verify ownership
    tts_request = db.query(TTSRequest).filter(
        TTSRequest.id == request_id,
        TTSRequest.user_id == user_id
    ).first()

    if not tts_request:
        raise HTTPException(status_code=404, detail="TTS request not found")

    # Save quality metric
    quality = AudioQualityMetric(
        tts_request_id=request_id,
        mos_score=payload.mos_score,
        intelligibility=payload.intelligibility
    )

    db.add(quality)
    db.commit()

    return {"message": "Feedback submitted successfully"}