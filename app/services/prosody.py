# ── Archive: original presets (v1) ───────────────────────────────────────────
# "happy":   {"pitch_shift": 0.05, "speed": 0.85, "energy_shift":  0.1},
# "sad":     {"pitch_shift":-0.05, "speed": 0.95, "energy_shift": -0.15},
# "neutral": {"pitch_shift": 0.0,  "speed": 1.0,  "energy_shift":  0.0},

# ── Archive: tuned presets (v2) ───────────────────────────────────────────────
# "happy":   {"pitch_shift": 0.05, "speed": 1.05, "energy_shift":  0.10},
# "sad":     {"pitch_shift":-0.15, "speed": 0.85, "energy_shift": -0.20},
# "neutral": {"pitch_shift": 0.0,  "speed": 1.0,  "energy_shift":  0.00},
# "angry":   {"pitch_shift": 0.10, "speed": 1.10, "energy_shift":  0.15},
# "fear":    {"pitch_shift": 0.10, "speed": 1.15, "energy_shift": -0.15},
# "surprise":{"pitch_shift": 0.10, "speed": 1.05, "energy_shift":  0.10},

# ── Archive: all-zero preset (v3 — too flat, all emotions sounded the same) ──
# "happy":   {"pitch_shift": 0.0, "speed": 1.0, "energy_shift": 0.0},
# "sad":     {"pitch_shift": 0.0, "speed": 1.0, "energy_shift": 0.0},
# "neutral": {"pitch_shift": 0.0, "speed": 1.0, "energy_shift": 0.0},
# "angry":   {"pitch_shift": 0.0, "speed": 1.0, "energy_shift": 0.0},
# "fear":    {"pitch_shift": 0.0, "speed": 1.0, "energy_shift": 0.0},
# "surprise":{"pitch_shift": 0.0, "speed": 1.0, "energy_shift": 0.0},

# ── CURRENT: Balanced human-like presets (v4) ─────────────────────────────────
# Speed is locked to 1.0 for all emotions to prevent librosa / FastSpeech
# alpha-scaling from introducing metallic / robotic phase-vocoder artifacts.
# Emotional character is delivered via pitch_shift + energy_shift + GST reference.
PROSODY_PRESETS = {
    # Brighter and more energetic — lifted pitch, louder delivery
    "happy":   {"pitch_shift":  0.05, "speed": 1.0, "energy_shift":  0.10},

    # Heavier and softer — lowered pitch, quieter voice
    "sad":     {"pitch_shift": -0.10, "speed": 1.0, "energy_shift": -0.15},

    # Flat baseline — no modification, reference delivery
    "neutral": {"pitch_shift":  0.00, "speed": 1.0, "energy_shift":  0.00},

    # Loud and tense — high pitch, strong volume boost
    "angry":   {"pitch_shift":  0.10, "speed": 1.0, "energy_shift":  0.20},

    # Timid and shaky — raised pitch but very quiet, like a hushed whisper
    "fear":    {"pitch_shift":  0.08, "speed": 1.0, "energy_shift": -0.15},

    # Startled pop — sharp pitch jump with a volume spike
    "surprise":{"pitch_shift":  0.12, "speed": 1.0, "energy_shift":  0.10},
}


def get_prosody(emotion: str):
    return PROSODY_PRESETS.get(emotion, PROSODY_PRESETS["neutral"])
