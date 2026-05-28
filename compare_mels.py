import torch
from app.services.fastspeech import FastSpeech2Service

service = FastSpeech2Service()

prosody = {
    "speed": 1.0,
    "pitch_shift": 0.0,
    "energy_shift": 0.0
}

# Run raw text2speech inference
ref = service._refs.get("Neutral")
with torch.no_grad():
    output = service.tts("This is a test of the local model.", speech=ref)

print("\n--- Output Keys in Model Output ---")
print(list(output.keys()))

for key in ["feat_gen", "feat_gen_denorm"]:
    if key in output:
        tensor = output[key]
        print(f"\n[{key}]")
        print(f"  Shape: {tensor.shape}")
        print(f"  Min:   {tensor.min().item():.4f}")
        print(f"  Max:   {tensor.max().item():.4f}")
        print(f"  Mean:  {tensor.mean().item():.4f}")

# Let's check if the stats file actually changes the denormalization!
# Print the config's stats file configuration
import yaml
with open(service._TRAIN_CONFIG, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

print("\n--- Config MVN Normalization Setup ---")
print("normalize:", cfg.get("normalize"))
print("normalize_conf:", cfg.get("normalize_conf"))
