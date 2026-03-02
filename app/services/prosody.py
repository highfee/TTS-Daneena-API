PROSODY_PRESETS = {
    "happy": {"pitch_shift": 0.15, "speed": 0.85, "energy_shift": 0.1},
    # Make "sad" less pitchy and with lower energy
    "sad": {"pitch_shift": -0.05, "speed": 0.95, "energy_shift": -0.15},
    "neutral": {"pitch_shift": 0.0, "speed": 1.0, "energy_shift": 0.0},
}


def get_prosody(emotion: str):
    return PROSODY_PRESETS.get(emotion, PROSODY_PRESETS["neutral"])
