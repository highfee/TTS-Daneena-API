import numpy as np
import librosa

EMOTION_PROFILES = {
    'Angry': {
        'tempo_factor':    1.10,
        'loudness_db':     5.0,
        'pitch_semitones': 0.5,    # was 2.0 — anger is tense, not high pitched
        'eq_profile':      'harsh',
    },
    'Happy': {
        'tempo_factor':    1.08,
        'loudness_db':     3.0,
        'pitch_semitones': 1.0,    # was 3.0 — slight lift, not chipmunk
        'eq_profile':      'bright',
    },
    'Neutral': {
        'tempo_factor':    1.00,
        'loudness_db':     0.0,
        'pitch_semitones': 0.0,
        'eq_profile':      'flat',
    },
    'Sad': {
        'tempo_factor':    0.82,
        'loudness_db':    -4.0,
        'pitch_semitones':-1.0,    # was -2.5 — subtle lowering sounds more natural
        'eq_profile':      'dull',
    },
    'Surprise': {
        'tempo_factor':    1.06,
        'loudness_db':     4.0,
        'pitch_semitones': 1.5,    # was 4.0 — was way too high
        'eq_profile':      'bright',
    },
    'Fear': {
        'tempo_factor':    1.15,
        'loudness_db':     2.0,
        'pitch_semitones': 1.0,    # was 3.5
        'eq_profile':      'bright',
    },
    'Disgust': {
        'tempo_factor':    0.92,
        'loudness_db':    -2.0,
        'pitch_semitones':-0.5,    # was -1.0
        'eq_profile':      'dull',
    },
    'Excited': {
        'tempo_factor':    1.15,
        'loudness_db':     5.0,
        'pitch_semitones': 1.5,    # was 3.0
        'eq_profile':      'bright',
    },
}

def apply_eq(wav: np.ndarray, sr: int, profile: str) -> np.ndarray:
    fft       = np.fft.rfft(wav)
    freqs     = np.fft.rfftfreq(len(wav), d=1/sr)
    magnitude = np.abs(fft)
    phase     = np.angle(fft)

    if profile == 'harsh':
        mask = (freqs >= 1000) & (freqs <= 4000)
        magnitude[mask] *= 1.6
    elif profile == 'bright':
        mask = (freqs >= 3000) & (freqs <= 8000)
        magnitude[mask] *= 1.5
    elif profile == 'dull':
        magnitude[freqs > 3000] *= 0.5
        magnitude[freqs < 500]  *= 1.3
    # flat: no change

    return np.fft.irfft(magnitude * np.exp(1j * phase), n=len(wav))

def apply_loudness(wav: np.ndarray, db: float) -> np.ndarray:
    return np.clip(wav * (10 ** (db / 20.0)), -1.0, 1.0)

def apply_tempo(wav: np.ndarray, sr: int, factor: float) -> np.ndarray:
    if abs(factor - 1.0) < 0.01:
        return wav
    return librosa.effects.time_stretch(wav, rate=factor)

def apply_pitch_shift(wav: np.ndarray, sr: int, semitones: float) -> np.ndarray:
    if abs(semitones) < 0.01:
        return wav
    return librosa.effects.pitch_shift(wav, sr=sr, n_steps=semitones)

def postprocess(wav: np.ndarray, sr: int, emotion: str) -> np.ndarray:
    # Case-insensitive lookup, fallback to Neutral
    profile = EMOTION_PROFILES.get(
        emotion.capitalize(),
        EMOTION_PROFILES['Neutral']
    )
    
    print(f"[PostProcess] emotion={emotion} "
          f"tempo={profile['tempo_factor']} "
          f"pitch={profile['pitch_semitones']} "
          f"loudness={profile['loudness_db']}dB")

    wav = apply_tempo(wav, sr, profile['tempo_factor'])
    wav = apply_pitch_shift(wav, sr, profile['pitch_semitones'])
    wav = apply_eq(wav, sr, profile['eq_profile'])
    wav = apply_loudness(wav, profile['loudness_db'])

    peak = np.abs(wav).max()
    if peak > 0.95:
        wav = wav * (0.95 / peak)

    return wav.astype(np.float32)