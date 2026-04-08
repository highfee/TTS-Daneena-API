from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class LatencyPoint(BaseModel):
    date: str
    avg_latency: float

class EmotionCount(BaseModel):
    emotion: str
    count: int

class AudioQualityStats(BaseModel):
    avg_mos: Optional[float] = None
    avg_intelligibility: Optional[float] = None

class PerformanceMetrics(BaseModel):
    avg_latency: float
    min_latency: int
    max_latency: int
    latency_trend: List[LatencyPoint]
    emotion_distribution: List[EmotionCount]
    audio_quality: AudioQualityStats

class FeedbackCreate(BaseModel):
    mos_score: int
    intelligibility: int
