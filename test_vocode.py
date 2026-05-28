import os
import torch
import numpy as np
import soundfile as sf
from app.services.fastspeech import FastSpeech2Service
from app.services.hifigan import HiFiGANService

print("Initializing Services...")
fastspeech = FastSpeech2Service()
hifigan = HiFiGANService()

prosody = {
    "speed": 1.0,
    "pitch_shift": 0.0,
    "energy_shift": 0.0
}

# 1. Synthesize mel using local model
text = "This is a test of the scaled vocoding pipeline."
print(f"Synthesizing: '{text}'")
mel = fastspeech.synthesize(text, prosody, "Neutral")

# Ensure mel is a torch tensor
if isinstance(mel, np.ndarray):
    mel = torch.from_numpy(mel)

print("\n--- Raw Mel Stats (ESPnet Base-10 log-mel) ---")
print(f"Shape: {mel.shape}")
print(f"Min:   {mel.min().item():.4f}")
print(f"Max:   {mel.max().item():.4f}")
print(f"Mean:  {mel.mean().item():.4f}")

# 2. Vocode UNSCALED
print("\nVocoding UNSCALED mel...")
try:
    wav_unscaled = hifigan.vocode(mel)
    # Normalize unscaled audio
    max_val = np.abs(wav_unscaled).max()
    if max_val > 0:
        wav_unscaled = wav_unscaled / max_val * 0.95
    sf.write("vocode_unscaled.wav", wav_unscaled, 22050)
    print("Saved: vocode_unscaled.wav")
except Exception as e:
    print("Error vocoding unscaled:", e)

# 3. Vocode SCALED (multiplied by ln(10) ~ 2.30258509 to convert base-10 to base-e)
print("\nVocoding SCALED mel (base-10 -> base-e via * 2.30258509)...")
try:
    # Scale by ln(10)
    mel_scaled = mel * np.log(10.0)
    print("--- Scaled Mel Stats (Natural log-mel) ---")
    print(f"Min:   {mel_scaled.min().item():.4f}")
    print(f"Max:   {mel_scaled.max().item():.4f}")
    print(f"Mean:  {mel_scaled.mean().item():.4f}")
    
    wav_scaled = hifigan.vocode(mel_scaled)
    # Normalize scaled audio
    max_val = np.abs(wav_scaled).max()
    if max_val > 0:
        wav_scaled = wav_scaled / max_val * 0.95
    sf.write("vocode_scaled.wav", wav_scaled, 22050)
    print("Saved: vocode_scaled.wav")
except Exception as e:
    print("Error vocoding scaled:", e)
