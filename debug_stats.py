# # save as debug_stats.py inside backend/
# import numpy as np, os

# base = os.path.dirname(os.path.abspath(__file__))
# stats_path = os.path.join(base, "training", "exp", "stats", "train", "feats_stats.npz")

# print(f"Looking for: {stats_path}")
# print(f"Exists: {os.path.isfile(stats_path)}")

# if os.path.isfile(stats_path):
#     s = np.load(stats_path)
#     print(f"Keys: {list(s.keys())}")
#     for k in s.keys():
#         arr = s[k]
#         print(f"  {k}: shape={arr.shape}  min={arr.min():.3f}  max={arr.max():.3f}")
# else:
#     print("❌ File not found — do you have stats copied locally?")
#     print("\nFiles in stats/train/:")
#     train_dir = os.path.join(base, "training", "exp", "stats", "train")
#     if os.path.isdir(train_dir):
#         for f in os.listdir(train_dir):
#             print(f"  {f}")
#     else:
#         print("  ❌ stats/train/ directory does not exist")

# in backend/
import sys, os, yaml
sys.path.insert(0, '.')
from app.services.fastspeech import _fixed_config_path

with open(_fixed_config_path(), encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

print("normalize stats_file:       ", cfg.get('normalize', {}).get('stats_file', 'NOT SET'))
print("pitch_normalize stats_file: ", cfg.get('pitch_normalize', {}).get('stats_file', 'NOT SET'))
print("energy_normalize stats_file:", cfg.get('energy_normalize', {}).get('stats_file', 'NOT SET'))