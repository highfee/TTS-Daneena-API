# debug_mel.py — run from backend/ folder
import torch, soundfile as sf, glob, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.services.fastspeech import _fixed_config_path, _MODEL_FILE, _REPO_ROOT
from espnet2.bin.tts_inference import Text2Speech

# Load model
print('Loading model...')
t2s = Text2Speech(
    train_config=_fixed_config_path(),
    model_file=_MODEL_FILE,
    device='cpu',
)
print('Model loaded.')

# Load reference audio
ref_path = os.path.join(_REPO_ROOT, 'data', 'resampled_wavs', '0011', 'Happy')
wavs = sorted(glob.glob(f'{ref_path}/*.wav'))
assert wavs, f'No wav files found in {ref_path}'

ref, _ = sf.read(wavs[0], dtype='float32')
if ref.ndim > 1:
    ref = ref.mean(axis=1)
ref_tensor = torch.tensor(ref)
print(f'Reference audio: {wavs[0]}')

# Run inference
with torch.no_grad():
    out = t2s("I am happy to see you today.", speech=ref_tensor)

fg  = out['feat_gen']
fgd = out['feat_gen_denorm']

print(f"\nfeat_gen:        min={fg.min():.3f}  max={fg.max():.3f}  mean={fg.mean():.3f}")
print(f"feat_gen_denorm: min={fgd.min():.3f}  max={fgd.max():.3f}  mean={fgd.mean():.3f}")
print(f"Are they identical? {torch.allclose(fg, fgd)}")
print(f"Max difference:     {(fg - fgd).abs().max():.4f}")