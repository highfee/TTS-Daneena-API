import os
import torch
import numpy as np
from app.services.fastspeech import FastSpeech2Service
from app.services.hifigan import HiFiGANService

print("Checking environment variable FORCE_FALLBACK:")
print("FORCE_FALLBACK =", os.environ.get("FORCE_FALLBACK"))

print("\nInitializing FastSpeech2Service...")
fastspeech = FastSpeech2Service()

print("\nInitializing HiFiGANService...")
hifigan = HiFiGANService()

print("\nSynthesizing test text with VITS fallback...")
prosody = {"speed": 1.0, "pitch_shift": 0.0, "energy_shift": 0.0}
res = fastspeech.synthesize("This is a test of the forced pretrained fallback system.", prosody, "Neutral")

print("\n--- Fallback Verification ---")
print("Result Type:", type(res))
if hasattr(res, "ndim") and res.ndim == 1:
    print("SUCCESS: Result is a 1-D waveform! (VITS direct neural vocoder output)")
    print(f"Waveform Min: {res.min().item() if hasattr(res.min(), 'item') else res.min():.4f}")
    print(f"Waveform Max: {res.max().item() if hasattr(res.max(), 'item') else res.max():.4f}")
else:
    print("WARNING: Result is not a 1-D waveform. Check your environment settings.")
