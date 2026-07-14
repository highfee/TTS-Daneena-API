

## Code Changes

### 1. `fastspeech.py` — Complete replacement

**What changed:** The entire service was rewritten. The old version loaded a locally trained FastSpeech2+GST model from disk, used ESPnet's `Text2Speech` class, required a reference audio per emotion for the GST encoder, and returned a 2-D mel spectrogram tensor for downstream HiFi-GAN vocoding. The new version loads XTTS-v2 from Coqui TTS, still uses one reference audio per emotion but now for voice cloning conditioning rather than style token extraction, and returns a 1-D waveform directly at 24,000 Hz — no separate vocoding step.

**Specific changes:**

- `from espnet2.bin.tts_inference import Text2Speech` → `from TTS.api import TTS`
- `Text2Speech(train_config=..., model_file=...)` → `TTS("tts_models/multilingual/multi-dataset/xtts_v2")`
- `self.tts(text, speech=ref, decode_conf={"alpha": alpha})` → `self.tts.tts(text, speaker_wav=ref_path, language="en")`
- Return type changed from `torch.Tensor (T, 80)` mel to `np.ndarray (N,)` waveform
- Added `torch.load` patch for PyTorch 2.6 `weights_only` compatibility
- Added `_download_refs_if_missing()` to fetch reference audio from HuggingFace at container startup since binary wav files cannot be pushed via git to HuggingFace Spaces
- Added `COQUI_TOS_AGREED=1` environment variable for non-interactive Docker builds
- Removed `_fixed_config_path()`, `_USE_FALLBACK`, `_TRAIN_CONFIG`, `_MODEL_FILE`, `_TRAIN_DIR` — all ESPnet-specific logic gone
- Sample rate changed from 22,050 Hz to 24,000 Hz

---

### 2. `tts_pipeline.py` — HiFi-GAN removed

**What changed:** HiFi-GAN is no longer needed since XTTS-v2 produces a waveform directly. The pipeline no longer routes 2-D mel output through a vocoder.

**Specific changes:**

- `from app.services.hifigan import HiFiGANService` — removed
- `hifigan = HiFiGANService()` — removed
- The `elif result.ndim == 2:` branch that called `hifigan.vocode(mel_tensor)` — replaced with a `RuntimeError` since a 2-D result should never occur with XTTS-v2
- `sf.write(file_path, audio, 22050)` → `sf.write(file_path, audio, 24000)` to match XTTS-v2's output sample rate
- Post-processing import added: `from app.services.emotion_postprocess import postprocess`
- `audio = postprocess(audio, sr=24000, emotion=emotion)` called after synthesis

---

### 3. `emotion_postprocess.py` — New file

**What changed:** This file did not exist in the original system. It was added to apply tempo and loudness shaping to the XTTS-v2 output, providing perceptual differentiation between emotion categories that the voice cloning model does not produce on its own.

**Contents:** Defines `EMOTION_PROFILES` dict mapping each emotion to a `tempo_factor` and `loudness_db` value. The `postprocess()` function applies `librosa.effects.time_stretch()` for tempo and a dB-to-linear amplitude multiplication for loudness, then normalises the peak to 0.95.

---

### 4. `hifigan.py` — No longer used

The HiFi-GAN service file remains on disk but is no longer imported or called anywhere in the pipeline. It can be retained for documentation purposes or removed.

---

### 5. `requirements.txt` — Major cleanup

**Removed:**
- `espnet`, `espnet_model_zoo` — ESPnet no longer used
- `pyworld` — ESPnet pitch extraction dependency, no longer needed
- `matplotlib`, `tensorboard` — training utilities, not needed in production
- `parallel-wavegan` — ESPnet vocoder dependency, removed
- `TTS==0.22.0` — replaced

**Added:**
- `coqui-tts` — XTTS-v2 provider
- `torch==2.1.0`, `torchaudio==2.1.0`, `torchvision==0.16.0` — pinned to prevent `torchcodec` incompatibility introduced in PyTorch 2.6

**Pinned:**
- `transformers==4.37.2` — required by coqui-tts; newer versions break the XTTS-v2 checkpoint load

---

### 6. `Dockerfile` — Two changes

**Removed:** `RUN python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng')"` — NLTK tagger no longer needed since XTTS-v2 uses its own grapheme-to-phoneme pipeline

**Added:** `ENV COQUI_TOS_AGREED=1` — required to bypass the interactive licence agreement prompt during non-interactive Docker builds. Without this the build hangs waiting for keyboard input and eventually fails with `EOFError`.