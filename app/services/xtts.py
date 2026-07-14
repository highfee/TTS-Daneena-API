



import os
import torch
import numpy as np
import urllib.request

os.environ["COQUI_TOS_AGREED"] = "1"

# ── Patch torch.load before ANY TTS import ────────────────────────────────────
_original_torch_load = torch.load
def _patched_torch_load(f, *args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _original_torch_load(f, *args, **kwargs)
torch.load = _patched_torch_load

from TTS.api import TTS

# ── Reference audio paths ─────────────────────────────────────────────────────
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
_REF_DIR = os.path.join(_REPO_ROOT, "data", "reference_audio")

_EMOTION_REF_PATHS = {
    "Angry":    os.path.join(_REF_DIR, "angry.wav"),
    "Happy":    os.path.join(_REF_DIR, "happy.wav"),
    "Neutral":  os.path.join(_REF_DIR, "neutral.wav"),
    "Sad":      os.path.join(_REF_DIR, "sad.wav"),
    "Surprise": os.path.join(_REF_DIR, "surprise.wav"),
    "Fear":     os.path.join(_REF_DIR, "surprise.wav"),
    "Disgust":  os.path.join(_REF_DIR, "neutral.wav"),
    "Excited":  os.path.join(_REF_DIR, "happy.wav"),
}

_FALLBACK_EMOTION = "Neutral"

# ── HF Space URL for reference audio download ─────────────────────────────────
_HF_BASE_URL = (
    "https://huggingface.co/spaces/HIghfee/daneena_tts"
    "/resolve/main/data/reference_audio"
)


class XTTSService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    # ── Download reference audio if missing ───────────────────────────────────
    def _download_refs_if_missing(self):
        os.makedirs(_REF_DIR, exist_ok=True)
        files = ["angry.wav", "happy.wav", "neutral.wav", "sad.wav", "surprise.wav"]
        for filename in files:
            out_path = os.path.join(_REF_DIR, filename)
            if not os.path.isfile(out_path):
                url = f"{_HF_BASE_URL}/{filename}"
                print(f"[TTS] Downloading {filename}...")
                try:
                    urllib.request.urlretrieve(url, out_path)
                    print(f"[TTS] ✅ {filename} downloaded")
                except Exception as e:
                    print(f"[TTS] ❌ Failed to download {filename}: {e}")
            else:
                print(f"[TTS] ✅ {filename} already exists locally")

    # ── Initialise model ──────────────────────────────────────────────────────
    def _init(self):
        # Step 1 — ensure reference audio is present
        self._download_refs_if_missing()

        # Step 2 — load XTTS-v2
        print("[TTS] Loading XTTS-v2 model...")
        self.tts = TTS(
            model_name="tts_models/multilingual/multi-dataset/xtts_v2",
            progress_bar=False,
        ).to("cuda" if torch.cuda.is_available() else "cpu")
        print("[TTS] XTTS-v2 loaded.")

        # Step 3 — verify reference audio
        print(f"[TTS] Reference audio directory: {_REF_DIR}")
        for emotion, path in _EMOTION_REF_PATHS.items():
            if os.path.isfile(path):
                size = os.path.getsize(path) / 1024
                print(f"[TTS] ✅ {emotion}: {os.path.basename(path)} ({size:.0f} KB)")
            else:
                print(f"[TTS] ⚠️  {emotion}: NOT FOUND — {path}")

    # ── Get reference path for emotion ───────────────────────────────────────
    def _get_ref_path(self, emotion: str) -> str | None:
        path = _EMOTION_REF_PATHS.get(
            emotion.capitalize(),
            _EMOTION_REF_PATHS[_FALLBACK_EMOTION]
        )
        if not os.path.isfile(path):
            print(f"[TTS] ⚠️  No ref for '{emotion}', falling back to Neutral")
            path = _EMOTION_REF_PATHS[_FALLBACK_EMOTION]
        # Final fallback — if neutral also missing return None
        if not os.path.isfile(path):
            return None
        return path

    # ── Synthesize 
    def synthesize(self, text: str, prosody: dict, emotion: str = "Neutral") -> np.ndarray:
        ref_path = self._get_ref_path(emotion)

        print(f"[TTS] Synthesizing | emotion={emotion} | "
              f"ref={os.path.basename(ref_path) if ref_path else 'default'}")

        if ref_path:
            wav = self.tts.tts(
                text=text,
                speaker_wav=ref_path,
                language="en",
            )
        else:
            # No reference audio available — use built-in XTTS speaker
            print("[TTS] ⚠️  Using built-in default speaker")
            wav = self.tts.tts(
                text=text,
                speaker="Claribel Dervla",
                language="en",
            )

        wav_np = np.array(wav, dtype=np.float32)

        # Normalize
        peak = np.abs(wav_np).max()
        if peak > 0:
            wav_np = wav_np / peak * 0.95

        print(f"[TTS] wav shape={wav_np.shape} "
              f"min={wav_np.min():.3f} max={wav_np.max():.3f}")
        return wav_np