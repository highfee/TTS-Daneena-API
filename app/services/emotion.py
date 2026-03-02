import functools
from transformers import pipeline

# Load once at startup — using top_k=1 to return only the best match (faster than return_all_scores=True)
emotion_classifier = pipeline(
    task="text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    top_k=1,
)

# Map model emotions to project emotions
EMOTION_MAP = {
    "joy": "happy",
    "sadness": "sad",
    "neutral": "neutral",
    "anger": "neutral",
    "fear": "neutral",
    "surprise": "happy",
    "disgust": "neutral",
}


@functools.lru_cache(maxsize=256)
def detect_emotion(text: str) -> tuple[str, float]:
    """
    Optimized emotion detection with:
    - top_k=1: only returns the highest-scoring label (skips scoring 6 other classes)
    - lru_cache: caches results for repeated inputs — no re-inference for identical text
    """
    result = emotion_classifier(text)
    # top_k=1 returns [[{'label': ..., 'score': ...}]]
    best = result[0][0]
    model_label = best["label"]
    score = best["score"]

    mapped_label = EMOTION_MAP.get(model_label, "neutral")
    return mapped_label, score
