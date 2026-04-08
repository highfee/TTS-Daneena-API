# PROSODY_PRESETS = {
#     "happy": {"pitch_shift": 0., "speed": 0.85, "energy_shift": 0.1},
#     # Make "sad" less pitchy and with lower energy
#     "sad": {"pitch_shift": -0.05, "speed": 0.95, "energy_shift": -0.15},
#     "neutral": {"pitch_shift": 0.0, "speed": 1.0, "energy_shift": 0.0},
# }

PROSODY_PRESETS = {
    # Higher pitch, faster tempo, and increased energy for a positive, vibrant tone
    "happy": {"pitch_shift": 0.15, "speed": 1.15, "energy_shift": 0.2},

    # Lower pitch, slower speed, and reduced energy to convey a somber, melancholic tone
    "sad": {"pitch_shift": -0.1, "speed": 0.7, "energy_shift": -0.3},

    # Baseline values for a standard, objective, and professional delivery
    "neutral": {"pitch_shift": 0.0, "speed": 1.0, "energy_shift": 0.0},

    # High pitch, fast pace, and strong energy for an intense, forceful tone
    "angry": {"pitch_shift": 0.20, "speed": 1.20, "energy_shift": 0.35},

    # Slightly raised pitch, faster pace, and reduced energy for a tense, anxious tone
    "fear": {"pitch_shift": 0.10, "speed": 1.10, "energy_shift": -0.10},

    # Elevated pitch and moderate energy increase for an exclamatory, startled tone
    "surprise": {"pitch_shift": 0.25, "speed": 1.05, "energy_shift": 0.15},
}


def get_prosody(emotion: str):
    return PROSODY_PRESETS.get(emotion, PROSODY_PRESETS["neutral"])
