from app.services.emotion import detect_emotion
from app.services.prosody import get_prosody


def analyze_text(text: str):
    emotion = detect_emotion(text)
    prosody = get_prosody(emotion)

    return {"text": text, "emotion": emotion, "prosody": prosody}
