import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env

import torch
import numpy as np

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent   # backend/
_EXP_DIR   = _REPO_ROOT / "training" / "exp" / "hifigan"
_HIFIGAN_REPO = _REPO_ROOT / "scripts" / "hifigan_repo"

# Auto-detect the latest fine-tuned generator checkpoint
def _find_finetuned():
    ckpts = sorted(_EXP_DIR.glob("g_*"))
    if ckpts:
        return ckpts[-1], _EXP_DIR / "config_emotional.json"
    return None, None


class HiFiGANService:
    """
    Vocoder that converts mel-spectrograms (80-band, 22050 Hz) to waveforms.

    Priority:
      1. Fine-tuned generator in training/exp/hifigan/  (best quality)
      2. Pretrained LJSpeech ESPnet model               (fallback)
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        # Force fallback if set in .env
        if os.environ.get("FORCE_FALLBACK", "0") == "1":
            print("[HiFiGAN] FORCE_FALLBACK=1 is active — completely forcing pretrained LJSpeech vocoder fallback.")
            self._load_pretrained()
            return

        ckpt_path, cfg_path = _find_finetuned()

        if ckpt_path and cfg_path and ckpt_path.exists() and cfg_path.exists():
            self._load_finetuned(ckpt_path, cfg_path)
        else:
            print("[HiFiGAN] Fine-tuned model not found — using pretrained LJSpeech fallback.")
            print("[HiFiGAN] Run scripts/finetune_hifigan.py to fine-tune on your dataset.")
            self._load_pretrained()

    # ── Fine-tuned loader ────────────────────────────────────────────────────
    def _load_finetuned(self, ckpt_path: Path, cfg_path: Path):
        # Add hifi-gan repo to path so we can import its Generator
        if str(_HIFIGAN_REPO) not in sys.path:
            sys.path.insert(0, str(_HIFIGAN_REPO))

        try:
            from models import Generator
            from env import AttrDict
        except ImportError as e:
            print(f"[HiFiGAN] Cannot import hifi-gan models ({e}). Falling back to pretrained.")
            self._load_pretrained()
            return

        with open(cfg_path) as f:
            h = AttrDict(json.load(f))

        generator = Generator(h).to("cpu")
        state = torch.load(str(ckpt_path), map_location="cpu")
        generator.load_state_dict(state["generator"])
        generator.eval()
        generator.remove_weight_norm()

        self._generator = generator
        self._mode = "finetuned"
        self._h = h
        print(f"[HiFiGAN] Loaded fine-tuned generator: {ckpt_path.name}")

    # ── Pretrained ESPnet fallback ───────────────────────────────────────────
    def _load_pretrained(self):
        from espnet2.bin.tts_inference import Text2Speech
        self._tts = Text2Speech.from_pretrained(
            model_tag="espnet/kan-bayashi_ljspeech_fastspeech2",
            device="cpu",
        )
        self._mode = "pretrained"
        print("[HiFiGAN] Pretrained LJSpeech vocoder ready.")

    # ── Public API ───────────────────────────────────────────────────────────
    def vocode(self, mel: torch.Tensor) -> np.ndarray:
        """Convert mel (T, n_mels) tensor → 1-D numpy float32 waveform."""
        if self._mode == "finetuned":
            return self._vocode_finetuned(mel)
        return self._vocode_pretrained(mel)

    def _vocode_finetuned(self, mel: torch.Tensor) -> np.ndarray:
        # Generator expects (1, n_mels, T)
        if mel.dim() == 2:
            mel = mel.T.unsqueeze(0)          # (T,80) → (1,80,T)
        elif mel.dim() == 3 and mel.shape[0] != 1:
            mel = mel.unsqueeze(0)
        with torch.no_grad():
            wav = self._generator(mel.to("cpu"))
        return wav.squeeze().cpu().numpy()

    def _vocode_pretrained(self, mel: torch.Tensor) -> np.ndarray:
        if self._tts.vocoder is None:
            raise RuntimeError("[HiFiGAN] No vocoder found in pretrained Text2Speech instance.")
        with torch.no_grad():
            mel = mel.to(self._tts.device)
            wav = self._tts.vocoder(mel)
        return wav.cpu().numpy()
