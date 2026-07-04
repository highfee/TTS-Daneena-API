import soundfile as sf
import numpy as np
import glob
import os

# ── Update this to match your actual path ─────────────────────────────────────
WAV_DIR = "/mnt/c/MIne/my work/eyes/Project_root/backend/data/resampled_wavs/0011"
OUT_DIR = "/mnt/c/MIne/my work/eyes/Project_root/backend/data/reference_audio"
os.makedirs(OUT_DIR, exist_ok=True)

EMOTIONS = ["Angry", "Happy", "Neutral", "Sad", "Surprise"]
TARGET_DURATION = 8.0
SR = 22050

for emotion in EMOTIONS:
    pattern = f"{WAV_DIR}/{emotion}/*.wav"
    wavs = sorted(glob.glob(pattern))
    
    # Debug — print what was found
    print(f"{emotion}: found {len(wavs)} files in {pattern}")
    
    if not wavs:
        print(f"  ❌ No files found — check path")
        continue

    combined = []
    total = 0.0

    for wav_path in wavs:
        audio, sr = sf.read(wav_path, dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        combined.append(audio)
        total += len(audio) / SR
        if total >= TARGET_DURATION:
            break

    merged = np.concatenate(combined)
    out_path = os.path.join(OUT_DIR, f"{emotion.lower()}.wav")
    sf.write(out_path, merged, SR)
    print(f"  ✅ {emotion}: {total:.1f}s → {out_path}")