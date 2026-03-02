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
}


def get_prosody(emotion: str):
    return PROSODY_PRESETS.get(emotion, PROSODY_PRESETS["neutral"])
