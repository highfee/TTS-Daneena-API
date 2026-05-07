# Notebook Walkthroughs

---

## FastSpeech2 Fine-Tuning Notebook (`fastspeech-fine-tune.ipynb`)

This notebook trains FastSpeech2 + GST on the ESD emotional speech dataset using ESPnet.
Every session follows the same order: Cell 1 → Cell 2 → Restart → Cell 3 through Cell 10.

---

### Cell 1 — GPU Check

Confirms a GPU is available before anything else runs. If no GPU is detected it stops
immediately with an error so we don't waste time running on CPU.

---

### Cell 2 — Install Dependencies

Installs ESPnet and all the supporting libraries the notebook needs (librosa, soundfile,
tgt for TextGrid parsing, etc.). It checks first whether ESPnet is already installed so
it skips the install on repeat runs — this is what makes "Save & Run All" work across
sessions without stopping at a manual restart point.

---

### Cell 3 — Paths & Checkpoint Restore

This is the most important setup cell. It does three things:

**1. Finds our datasets**
Scans `/kaggle/input` to locate the ESD wav files, the ESPnet data folder, and the
checkpoint dataset if we attached one.

**2. Sets up all working paths**
Defines every folder the notebook will use — where data lives, where the model saves
checkpoints, where stats are stored — and creates them if they don't exist.

**3. Restores a previous training session**
If a checkpoint dataset is attached, it copies the model weights, config, token list,
and stats files back into the right locations. It then wraps the weights into a
`checkpoint.pth` file that ESPnet's trainer can actually read for resuming — because
ESPnet only looks for that specific filename, not the `valid.loss.best.pth` file we
saved.

> **The one line we update every session:**
>
> ```python
> RESUMED_FROM_EPOCH = 40  # change to the last completed epoch
> ```

---

### Cell 4 — Copy ESPnet Data & Fix wav.scp Paths

The ESD dataset attached to Kaggle has wav file paths from wherever it was originally
created (e.g. a Windows machine or another Kaggle session). This cell copies the data
into the working directory and rewrites every wav path to point to the correct Kaggle
location (`/kaggle/input/.../resampled_wavs/...`). Without this, ESPnet can't find
any audio files.

---

### Cell 5 — MFA Alignment & Duration Extraction

This is the longest cell and the most complex. It does three things in sequence:

**1. Installs MFA (Montreal Forced Aligner)**
MFA is a separate tool (not a Python package) that aligns audio to text at the
phoneme level — it figures out exactly when each sound starts and ends in the
recording. Installing it requires Miniforge (a conda installer) because MFA depends
on Kaldi, which can't be installed via pip.

**2. Runs alignment**
Organises all audio files and transcripts by speaker, then runs MFA to produce
TextGrid files — these are timestamped phoneme boundaries for every utterance.

**3. Extracts frame-level durations**
Converts the TextGrid timestamps into integer frame counts (how many mel frames each
phoneme spans). These durations are clamped to exactly match the mel spectrogram
length to prevent the off-by-one errors that would crash training later.

---

### Cell 6 — Build Token List

Reads all the phoneme labels produced by MFA and builds the vocabulary file
(`tokens.txt`) that ESPnet uses as its alphabet. It always starts with `<blank>` and
`<unk>` and ends with `<sos/eos>` — these are special tokens ESPnet requires.

---

### Cell 7 — Patch ESPnet & Compute Stats

Two jobs in one cell:

**1. Patches ESPnet's source code**
Applies four in-memory fixes to ESPnet bugs that would crash training:

- `dio.py` — stops a crash when pitch extraction runs without duration targets
- `energy.py` — same fix for energy extraction
- `fastspeech2.py` — trims tensors before the duration predictor to prevent
  size mismatches from the off-by-one frame counting issue
- `loss.py` — trims pitch and energy predictions to match target lengths before
  computing the loss

After patching it reloads the modules in memory so the fixes are live without
restarting the kernel.

**2. Computes normalisation statistics**
Runs ESPnet's `collect_stats` pass over the training and validation data to compute
the mean and standard deviation of mel features, pitch, and energy. These stats are
saved as `.npz` files and used later to normalise the data during training.

---

### Cell 8 — Write Training Config

Writes the YAML config file that controls all training hyperparameters. Key settings:

- **Mel config** — `n_fft=1024, hop=256, n_mels=80, sr=22050, fmin=80, fmax=7600`
  (must match HiFi-GAN exactly)
- **GST settings** — 10 style tokens, 4 attention heads, 6 conv layers
- **Optimiser** — Adam with `lr=5e-4`, warmup over 1000 steps
- **Grad clip** — 5.0 (allows gradients up to 5× before clipping)
- **Max epoch** — set to however many epochs we want this session to run

It also auto-validates the GST config keys against the installed ESPnet version and
removes any that aren't supported, so the config never breaks on version mismatches.

---

### Cell 9 — Train

Launches training by calling `TTSTask.main()` directly in-process (no subprocess).
ESPnet handles everything from here — batching, loss computation, validation, saving
checkpoints every N epochs. With `--resume true` it automatically picks up from
`checkpoint.pth` if one exists.

Training logs appear in real time. Watch for:

- `clip%` dropping from high (>50%) to low (<10%) as training stabilises
- `valid/loss` decreasing each epoch
- `The best model has been updated` to confirm checkpoints are saving

---

### Cell 10 — Package Checkpoint

Packages only the files needed to resume training or run inference:

| File                        | Purpose                                         |
| --------------------------- | ----------------------------------------------- |
| `valid.loss.best.pth`       | Best model by validation loss                   |
| `valid.loss.ave_10best.pth` | Average of 10 best checkpoints (better quality) |
| `train.loss.ave_10best.pth` | Average of 10 best by training loss             |
| `config.yaml`               | Model architecture and training config          |
| `tokens.txt`                | Phoneme vocabulary                              |
| `feats_stats.npz`           | Mel normalisation stats                         |
| `pitch_stats.npz`           | Pitch normalisation stats                       |
| `energy_stats.npz`          | Energy normalisation stats                      |

It then **deletes everything else** in `/kaggle/working` so Kaggle's automatic
output zip stays small (~300MB instead of 20GB). We download
`fastspeech2_gst_checkpoint.zip` and re-upload it as the `fastspeech2-gst-checkpoint`
Kaggle dataset before the next session.

---

---

## HiFi-GAN Fine-Tuning Notebook (`hifigan-train.ipynb`)

This notebook fine-tunes the HiFi-GAN vocoder on ESD audio so it can accurately
render the emotional mel spectrograms that FastSpeech2 produces.

---

### Cell 1 — GPU Check

Same as the FastSpeech2 notebook — confirms a GPU is available. HiFi-GAN uses 2× T4
GPUs (`GPU T4 x2` in settings) for faster training since GAN training is more
computationally intensive.

---

### Cell 2 — Install Dependencies

Installs `gdown` (for downloading pretrained weights from Google Drive), `librosa`,
`soundfile`, and `tqdm`. Requires a session restart after completing.

---

### Cell 3 — Setup Paths

Finds the ESD wav dataset and optional checkpoint dataset, then defines all working
directories. Prints a summary so we can confirm everything is found before proceeding.

---

### Cell 4 — Clone Repo & Download Pretrained Weights

Does two things:

**1. Clones the HiFi-GAN repository** from GitHub — this is the actual model code,
training loop, and dataset loader. HiFi-GAN is not a pip package so it must be
cloned directly.

**2. Downloads UNIVERSAL_V1 pretrained weights** from Google Drive — these are the
starting point for fine-tuning. Training from random initialisation would take
hundreds of thousands of steps; starting from pretrained weights that already know
how to vocode speech means fine-tuning on ESD audio converges much faster.

---

### Cell 5 — Build Config & Filelists

Two jobs:

**1. Writes the HiFi-GAN config** (`config_emotional.json`) — controls the model
architecture and mel parameters. The mel settings here must exactly match what
FastSpeech2 uses:

```
n_fft=1024, hop_size=256, n_mels=80, sr=22050, fmin=80, fmax=7600
```

If these don't match, the vocoder will receive mels it wasn't trained on and produce
distorted audio.

**2. Builds train/valid file lists** — walks all ESD wav files and splits them 95/5
into training and validation lists. These text files are what HiFi-GAN's data loader
reads to find audio during training.

---

### Cell 6 — Patch `meldataset.py`

The HiFi-GAN repo was written for older versions of PyTorch and librosa. Four patches
make it compatible with the versions available on Kaggle:

- **Patch 1** — uses `fmin`/`fmax` from the config file instead of hardcoded
  `0` and `8000`, so the mel filter bank matches what FastSpeech2 uses
- **Patch 2** — updates the `librosa.filters.mel()` call to use keyword arguments,
  required since librosa 0.10
- **Patch 3** — adds `return_complex=True` to `torch.stft()`, required since
  PyTorch 2.0
- **Patch 4** — updates the magnitude calculation to work with complex tensors
  produced by the patched STFT call

Without these patches the training cell crashes immediately on the first batch.

---

### Cell 7 — Restore Checkpoint or Seed from Pretrained

Decides where training will start from:

**If a checkpoint dataset is attached** (resuming across sessions): copies the
generator (`g_*`) and discriminator (`do_*`) checkpoint files back into the working
directory. HiFi-GAN automatically detects the highest-numbered checkpoint and resumes
from there. If only the generator was saved (no discriminator), it creates a synthetic
discriminator checkpoint using the pretrained weights so the step counter is correct.

**If no checkpoint is attached** (fresh run): copies the pretrained UNIVERSAL_V1
weights into `g_00000000` and `do_00000000` — step zero — so training begins from a
pre-trained starting point rather than random noise.

---

### Cell 8 — Fine-Tune HiFi-GAN

Launches training. Before starting it patches `train.py` to add a hard stop at
`MAX_STEPS=300,001` — without this HiFi-GAN would run indefinitely since its
`training_epochs=9999` is effectively infinite.

Training runs until it hits the step limit or the session ends. Checkpoints are saved
every 20,000 steps. The training logs print loss values every 100 steps and validation
scores every 20,000 steps.

To resume in a new session: run Cell 9 first to save the checkpoint, re-upload it as
the `hifigan-checkpoint` dataset, then Cell 7 will pick it up automatically.

---

### Cell 9 — Package Checkpoint

Saves the latest generator and discriminator checkpoints plus the config file into
`/kaggle/working/hifigan_trained/`. Both `g_*` and `do_*` files are needed for a
clean resume — saving only the generator means the discriminator restarts from
pretrained weights next session, which slightly degrades quality continuity.

We re-upload the contents of this folder as the `hifigan-checkpoint` Kaggle dataset
before the next session.
