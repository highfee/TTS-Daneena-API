import os
import re
import tempfile

import nltk
import soundfile as sf
import torch
import yaml
from espnet2.bin.tts_inference import Text2Speech

try:
    nltk.data.find("taggers/averaged_perceptron_tagger_eng")
except LookupError:
    nltk.download("averaged_perceptron_tagger_eng")

# ── Paths ─────────────────────────────────────────────────────────────────────
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
_TRAIN_DIR = os.path.join(_REPO_ROOT, "training", "exp", "tts_fastspeech2_gst")
# Use the ESPnet-saved output config — it has token_list, all model params,
# and stats paths already merged from the training CLI args.
_TRAIN_CONFIG = os.path.join(_TRAIN_DIR, "config.yaml")
# Prefer 10-best averaged model (better quality); fall back to single best
_MODEL_FILE = (
    os.path.join(_TRAIN_DIR, "valid.loss.ave_10best.pth")
    if os.path.isfile(os.path.join(_TRAIN_DIR, "valid.loss.ave_10best.pth"))
    else os.path.join(_TRAIN_DIR, "valid.loss.best.pth")
)

# Fall back to the pretrained LJSpeech model while your model is still training.
# Set FORCE_FALLBACK=1 to bypass local model even if it exists.
_USE_FALLBACK = (
    os.environ.get("FORCE_FALLBACK", "0") == "1"
    or not (os.path.isfile(_TRAIN_CONFIG) and os.path.isfile(_MODEL_FILE))
)

# ── GST reference audio ───────────────────────────────────────────────────────
# One short, clean sample per emotion.  The GST encoder reads its mel features
# and produces a style embedding that colours the synthesised speech.
_REF_SPK = "0011"
_EMOTION_REF_PATHS = {
    "Angry":    os.path.join(_REPO_ROOT, "data", "resampled_wavs", _REF_SPK, "Angry",    f"{_REF_SPK}_000351.wav"),
    "Happy":    os.path.join(_REPO_ROOT, "data", "resampled_wavs", _REF_SPK, "Happy",    f"{_REF_SPK}_000701.wav"),
    "Neutral":  os.path.join(_REPO_ROOT, "data", "resampled_wavs", _REF_SPK, "Neutral",  f"{_REF_SPK}_000001.wav"),
    "Sad":      os.path.join(_REPO_ROOT, "data", "resampled_wavs", _REF_SPK, "Sad",      f"{_REF_SPK}_001051.wav"),
    "Surprise": os.path.join(_REPO_ROOT, "data", "resampled_wavs", _REF_SPK, "Surprise", f"{_REF_SPK}_001401.wav"),
}


def _fixed_config_path() -> str:
    """
    The training config stores absolute WSL paths like /mnt/c/MIne/... for
    stats_file entries.  When loading the model on Windows those paths don't
    exist.  This function rewrites any stats_file value that points inside the
    repo so it uses the current _REPO_ROOT, then saves a patched copy to a
    temp file and returns its path.
    """
    _STATS_DIR = os.path.join(_REPO_ROOT, "training", "exp", "stats")

    with open(_TRAIN_CONFIG, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # The config may have paths from different training environments, e.g.:
    #   /mnt/c/.../training/exp/stats/train/feats_stats.npz  (local WSL)
    #   /kaggle/working/esd_tts/exp/stats/train/feats_stats.npz  (Kaggle)
    # Match any path that ends with .../exp/stats/<rest> and rewrite to _STATS_DIR/<rest>.
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

    fixed_cfg = _walk(cfg)

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    )
    yaml.dump(fixed_cfg, tmp, default_flow_style=False, allow_unicode=True)
    tmp.close()
    return tmp.name



# remove later
# import numpy as np
# stats_path = os.path.join(_REPO_ROOT, "training", "exp", "stats", "train", "feats_stats.npz")
# if os.path.isfile(stats_path):
#     s = np.load(stats_path)
#     print(f"[FastSpeech2] feats_stats mean range: {s['mean'].min():.3f} to {s['mean'].max():.3f}")
#     print(f"[FastSpeech2] feats_stats std range:  {s['std'].min():.3f} to {s['std'].max():.3f}")
# else:
#     print(f"[FastSpeech2] ❌ feats_stats.npz NOT FOUND at {stats_path}")

# =================

class FastSpeech2Service:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    # ------------------------------------------------------------------
    def _init(self):
        if _USE_FALLBACK:
            print(
                "[FastSpeech2] Local trained model not found — "
                "using pretrained LJSpeech fallback (no GST)."
            )
            self.tts = Text2Speech.from_pretrained(
                model_tag="espnet/kan-bayashi_ljspeech_fastspeech2",
                device="cpu",
            )
            self._refs = {}
            self._has_gst = False
        else:
            print(f"[FastSpeech2] Loading local model: {_MODEL_FILE}")
            self.tts = Text2Speech(
                train_config=_fixed_config_path(),
                model_file=_MODEL_FILE,
                device="cpu",
            )
            # Detect model type from config
            with open(_TRAIN_CONFIG, "r", encoding="utf-8") as f:
                _cfg = yaml.safe_load(f)
            self._model_type = _cfg.get("tts", "fastspeech2").lower()

            # Detect GST/style encoder — attribute name varies by ESPnet version
            tts_inner = self.tts.model.tts
            self._has_gst = (
                hasattr(tts_inner, "gst")
                or hasattr(tts_inner, "style_encoder")
                or "speech" in self.tts.__call__.__code__.co_varnames
            )

            # Pre-load reference audios (raw float32 numpy, 22 050 Hz mono)
            self._refs: dict[str, object] = {}
            for emotion, path in _EMOTION_REF_PATHS.items():
                if os.path.isfile(path):
                    wav, _ = sf.read(path, dtype="float32")
                    if wav.ndim > 1:
                        wav = wav.mean(axis=1)      # stereo → mono
                    self._refs[emotion] = wav
                else:
                    print(f"[FastSpeech2] Reference audio missing: {path}")

    # ------------------------------------------------------------------
    def synthesize(self, text: str, prosody: dict, emotion: str = "Neutral"):
        """Return a denormalised mel-spectrogram tensor (T, n_mels)."""

        # Always pass a reference audio for the local model — the GST encoder
        # requires it. For the pretrained fallback _refs is empty so ref=None.
        ref = self._refs.get(emotion)
        if ref is None:
            ref = self._refs.get("Neutral")

        # alpha speed control only works with FastSpeech2, not Tacotron2
        speed = max(prosody.get("speed", 1.0), 0.1)
        alpha = 1.0 / speed

        with torch.no_grad():
            is_tacotron = getattr(self, "_model_type", "fastspeech2") == "tacotron2"
            if is_tacotron:
                output = self.tts(text, speech=ref)
            else:
                output = self.tts(text, speech=ref, decode_conf={"alpha": alpha})

        print(f"[FastSpeech2] output keys: {list(output.keys())}")

        # For the local Tacotron2 model always use the mel → HiFiGAN path.
        # Griffin-Lim (ESPnet's built-in vocoder) produces robotic audio;
        # the fine-tuned HiFiGAN gives significantly better quality.
        # For the pretrained LJSpeech fallback, use its built-in vocoder (wav).
        if _USE_FALLBACK and "wav" in output:
            wav = output["wav"]
            if hasattr(wav, 'squeeze'):
                wav = wav.squeeze()
            print(f"[FastSpeech2] built-in vocoder wav: shape={wav.shape} min={wav.min():.3f} max={wav.max():.3f}")
            return wav

        # Local model: return mel for HiFiGAN vocoding.
        # ESPnet returns feat_gen_denorm when a normaliser is configured,
        # otherwise falls back to feat_gen.
        mel = output.get("feat_gen_denorm", output.get("feat_gen"))
        if mel is None:
            mel = next(iter(output.values()))

        print(f"[FastSpeech2] mel shape={mel.shape} min={mel.min():.3f} max={mel.max():.3f} mean={mel.mean():.3f}")
        return mel
    # def synthesize(self, text: str, prosody: dict, emotion: str = "Neutral"):
    #     """
    #     Return a denormalised mel-spectrogram tensor (T, n_mels).
    #     Optimized for GST-only models and 300k HiFi-GAN.
    #     """
    #     import torch
    #     import numpy as np

    #     # 1. Load Reference Audio (GST)
    #     # The GST encoder uses this to extract the "vibe" of the emotion.
    #     ref = self._refs.get(emotion)
    #     if ref is None:
    #         ref = self._refs.get("Neutral")
        
    #     # Convert numpy array to torch tensor
    #     ref_tensor = torch.from_numpy(ref).float()

    #     # 2. Extract Prosody Presets from prosody.py
    #     # Your notebook training supports speed (alpha), pitch, and energy controls.
    #     speed = max(prosody.get("speed", 1.0), 0.1)
    #     alpha = 1.0 / speed
        
    #     # FastSpeech2 allows us to physically shift these values
    #     p_control = prosody.get("pitch_shift", 1.0)
    #     e_control = prosody.get("energy_shift", 1.0)

    #     # 3. Run Inference
    #     with torch.no_grad():
    #         # FastSpeech2 standard inference config
    #         # We remove pitch_control and energy_control to avoid the TypeError
    #         decode_conf = {
    #             "alpha": alpha,  # This controls speed (1.0 / speed)
    #         }
            
    #         # If you want to try the other common ESPnet names for these, 
    #         # they are sometimes 'pitch_alpha' and 'energy_alpha', 
    #         # but 'alpha' is the only one guaranteed to work in all versions.
            
    #         output = self.tts(
    #             text, 
    #             speech=ref_tensor, 
    #             # sids=sid_tensor,  # Omitted as per your notebook config
    #             decode_conf=decode_conf
    #         )

    #     # 4. Extract Mel-spectrogram
    #     # We prioritize feat_gen_denorm which uses your feats_stats.npz
    #     mel = output.get("feat_gen_denorm")
    #     if mel is None:
    #         mel = output.get("feat_gen")
        
    #     # 5. Dynamic Range Check (The "Tone" Prevention)
    #     # HiFi-GAN expects clear contrast. If min is above -6.0, the audio 
    #     # will sound like a monotone buzzing 'tone'.
    #     curr_min = mel.min().item()
    #     if curr_min > -7.0:
    #         print(f"[FastSpeech2] Found shallow mel range (min={curr_min:.2f}). Applying contrast stretch...")
    #         # Scale the mel to sit between -11.5 (silence) and 0.5 (speech)
    #         # This turns the "buzz" back into clear speech.
    #         mel = ((mel - mel.mean()) * 3.8) - 7.5

    #     print(f"[FastSpeech2] Final Output: min={mel.min():.2f} max={mel.max():.2f}")
    #     return mel
