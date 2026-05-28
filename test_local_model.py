import torch
import numpy as np
from app.services.fastspeech import FastSpeech2Service

print("Initializing FastSpeech2Service (Local Model)...")
service = FastSpeech2Service()

prosody = {
    "speed": 1.0,
    "pitch_shift": 0.0,
    "energy_shift": 0.0
}

print("Synthesizing test sentence...")
res = service.synthesize("This is a test of the local model.", prosody, "Neutral")

print("\n--- Synthesis Result ---")
print("Type:", type(res))
if hasattr(res, "shape"):
    print("Shape:", res.shape)
    val_min = res.min().item() if hasattr(res, "min") else res.min()
    val_max = res.max().item() if hasattr(res, "max") else res.max()
    val_mean = res.mean().item() if hasattr(res, "mean") else res.mean()
    print(f"Min:  {val_min:.4f}")
    print(f"Max:  {val_max:.4f}")
    print(f"Mean: {val_mean:.4f}")
    
    if res.ndim == 2:
        print("\nThis is a 2D Mel-Spectrogram (T, n_mels) as expected for the local model!")
    elif res.ndim == 1:
        print("\nThis is a 1D Waveform (T,)!")
else:
    print("Result does not have a shape attribute.")
