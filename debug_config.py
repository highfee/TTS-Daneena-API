# debug_config.py in backend/
import os, yaml, re

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
_TRAIN_DIR = os.path.join(_REPO_ROOT, 'training', 'exp', 'tts_fastspeech2_gst')
_TRAIN_CONFIG = os.path.join(_TRAIN_DIR, 'config.yaml')
_STATS_DIR = os.path.join(_REPO_ROOT, 'training', 'exp', 'stats')
_stats_pattern = re.compile(r".+?[/\\]exp[/\\]stats[/\\](.+)")

def _fix_value(v):
    if isinstance(v, str):
        m = _stats_pattern.match(v)
        if m:
            return os.path.join(_STATS_DIR, m.group(1)).replace("\\", "/")
    return v

def _walk(obj):
    if isinstance(obj, dict):
        return {k: _walk(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_walk(i) for i in obj]
    return _fix_value(obj)

with open(_TRAIN_CONFIG, encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

fixed = _walk(cfg)
# Replace the print block at the bottom with this:
import json

# Print the full config so we can find the stats paths
print(json.dumps(fixed, indent=2, default=str))