# TTS System: How It All Works

## The Big Picture

Think of converting text to speech like a two-stage art process:

```

Your Text → [Stage 1: FastSpeech2 + GST] → Blueprint → [Stage 2: HiFi-GAN] → Audio

```

**Stage 1** reads your text and draws a "blueprint" of what the sound should look like
— called a mel spectrogram. Think of it like sheet music.

**Stage 2** takes that sheet music and actually performs it — producing the real audio
waveform you hear.

They are two separate models because designing music and performing it are two very
different skills.

---

## Fallback Strategy — Pretrained Models

Both models have a fallback in case the fine-tuned versions are not available:

### FastSpeech2 fallback

If the local trained model files (`config.yaml` + `valid.loss.ave_10best.pth`) are not
found on disk — or if `FORCE_FALLBACK=1` is set — the system automatically loads the
publicly pretrained **ESPnet LJSpeech FastSpeech2** model instead:

```python
_USE_FALLBACK = (
    os.environ.get("FORCE_FALLBACK", "0") == "1"
    or not (os.path.isfile(_TRAIN_CONFIG) and os.path.isfile(_MODEL_FILE))
)
```

The fallback model works and produces intelligible speech, but it has no GST and no
emotional awareness — every sentence comes out in the same calm, neutral, American
female voice regardless of what emotion was detected.

### HiFi-GAN fallback

If the fine-tuned HiFi-GAN generator checkpoint (`g_00XXXXXX`) or its config
(`config_emotional.json`) is not found in `training/exp/hifigan/`, the system falls
back to the vocoder bundled inside the pretrained LJSpeech ESPnet model.

The fallback vocoder works but was trained on LJSpeech audio — so when paired with
the fine-tuned FastSpeech2 it produces slightly buzzy or muffled output because the
two models were trained on different audio distributions.

### In short

The system always produces audio — fallbacks ensure it never crashes in development
or before training is complete. But the best quality only comes when both fine-tuned
models are present.

---

## Why We Fine-Tuned FastSpeech2

### The out-of-the-box problem

The pretrained FastSpeech2 was trained on one person — a neutral American woman
reading audiobooks (LJSpeech). It only knows one voice, one style, one emotion:
calm and flat.

If you asked it to sound angry or happy, it would still produce the same neutral,
monotone output. It simply has no concept of emotion.

### What fine-tuning on ESD did

The ESD dataset has 10 speakers each saying the same sentences in 5 different
emotions. By training on this, FastSpeech2 learned:

- **Angry speech** has higher energy, faster tempo, sharper pitch changes
- **Sad speech** is slower, lower in pitch, quieter
- **Happy speech** has rising pitch, more energy variation
- **Surprised speech** has sudden pitch jumps
- **Neutral speech** is calm and even — the baseline

### What GST adds

GST stands for Global Style Tokens. Think of it as a **mood dial** the model learns
during training.

Instead of hardcoding "angry = raise pitch by X", the model learns a flexible style
space on its own. At inference time you hand it a short reference audio clip of
someone speaking angrily, and the GST encoder reads that clip and sets the mood dial
accordingly. The model then generates speech with that emotional flavour baked in.

Without GST, FastSpeech2 has no mechanism to accept emotional input at all.

---

## Why We Fine-Tuned HiFi-GAN

### The mismatch problem

HiFi-GAN is the performer that turns sheet music into sound. But imagine training a
pianist on classical music, then handing them jazz sheet music and expecting them to
perform it naturally — the notes are there but the style is wrong.

The pretrained HiFi-GAN learned to convert **LJSpeech-style** mel spectrograms into
audio. Your FastSpeech2 now produces **ESD emotional speech** mel spectrograms — a
completely different style. Feeding ESD mels to an LJSpeech vocoder produces buzzy,
robotic, or muffled audio because the vocoder is seeing patterns it was never trained on.

### What fine-tuning HiFi-GAN did

By fine-tuning on ESD audio, HiFi-GAN learned the specific sonic fingerprint of your
10 speakers and their emotional expressions. At 240k steps it reached a mel
reconstruction error of ~0.28 — meaning it closely reproduces the exact mel patterns
that FastSpeech2 produces, resulting in clean, natural-sounding audio.

---

## Why FastSpeech2 Needed Patching

FastSpeech2 works by:

1. Reading your text phoneme by phoneme
2. Deciding how long each phoneme should last (duration)
3. Stretching the hidden representation to match that duration
4. Predicting pitch and energy for each frame
5. Generating the mel spectrogram

The bug was a **counting disagreement**. Two different parts of ESPnet were counting
audio frames using slightly different math formulas. They almost always agreed —
except by exactly 1 frame at the boundary. So one part thought a sentence was 38
frames long, another thought 39.

When the model tried to compare its 39-frame prediction against a 38-frame ground
truth to compute the loss, PyTorch crashed rather than silently doing the wrong thing.

Four patches were applied:

- **Patch 1 & 2 — `dio.py` and `energy.py`**: Guarded against a `None` duration
  value during stats collection, which crashed when the model tried to multiply
  `None` by the reduction factor.

- **Patch 3 — `fastspeech2.py`**: Trimmed the encoder hidden states to match the
  duration target length before running the duration predictor, preventing
  mismatched tensor sizes flowing into the variance predictors.

- **Patch 4 — `loss.py`**: Even after patch 3, pitch and energy predictions were
  still off by 1 because they run after the length regulator expands frames using
  duration sums. The fix trims both prediction and target to the shorter length
  before computing the MSE loss — essentially saying "use whichever length is
  shorter, don't crash."

This is a known rough edge in ESPnet's FastSpeech2 implementation when using
external MFA alignments instead of ESPnet's built-in aligner.

---

## The Full Pipeline at Inference

Here is what happens when your API receives a text request:

```
User sends: "I am so happy to see you!"
```

**Step 1 — Emotion Detection** (`emotion.py`)
The text is classified as `Happy` with a confidence score.

**Step 2 — Prosody Mapping** (`prosody.py`)
`Happy` is mapped to speed/pitch/energy settings — e.g. slightly faster speed,
higher energy.

**Step 3 — FastSpeech2 synthesis** (`fastspeech.py`)

- Checks whether the fine-tuned model is available. If not, loads the LJSpeech
  pretrained fallback instead.
- Loads a reference audio clip of a Happy speaker from `_EMOTION_REF_PATHS`.
- Feeds the text + reference audio into the model.
- The GST encoder reads the reference audio and sets the style embedding.
- FastSpeech2 generates a mel spectrogram shaped `(T, 80)` — T frames, 80 mel bands.
- Returns `feat_gen_denorm` — the mel scaled back to real acoustic values using the
  training stats (`feats_stats.npz`).

**Step 4 — HiFi-GAN vocoding** (`hifigan.py`)

- Checks whether the fine-tuned generator is available. If not, uses the pretrained
  LJSpeech vocoder as fallback.
- Receives the mel spectrogram `(T, 80)`.
- Reshapes it to `(1, 80, T)` — what the generator expects.
- Runs it through the fine-tuned generator.
- Outputs a raw waveform — a 1D array of audio samples at 22050 Hz.

**Step 5 — Post-processing** (`tts_pipeline.py`)

- Normalises the audio amplitude to prevent clipping.
- Saves it as a `.wav` file.
- Caches the result so repeated identical requests skip the entire ML pipeline.
- Returns the file path to the API route which streams it back to the client.

```
Full flow:

Text → emotion tag → prosody → reference audio → mel spectrogram → waveform → .wav
         (fast)       (map)      (lookup)          (FastSpeech2)    (HiFiGAN)   (saved)
```

---

## Why the Audio Currently Sounds Like a Tone

At epoch 210, the model is still learning. The mel spectrogram it produces has a very
narrow value range — like a musical score where all the notes are clustered in one
octave instead of spanning the full range. HiFi-GAN faithfully converts this
compressed mel into audio, which comes out as a steady tone rather than speech.

As training continues the audio will progressively improve

Both models are always loaded in the correct priority order — fine-tuned first,
pretrained fallback second — so the system produces the best audio it can at any
stage of training.
