# Changes Required in Daneena Update.docx

Each item shows: where to find the text, what to delete, and the exact replacement to paste in.

---

## FACTUAL ERRORS

---

### 1. Section 3.3 — Model identifier incomplete

**Find and replace every occurrence of:**

```
emotion-english-distilroberta-base
```

**With:**

```
j-hartmann/emotion-english-distilroberta-base
```

---

### 2. Section 3.6.3 — Model checkpoint filename

**Find:**

```
FastSpeech2Service checks whether a locally trained model exists at the path
training/exp/tts_fastspeech2_gst/valid.loss.best.pth. If this file is not found, the
service automatically downloads and loads the pre-trained ESPnet LJSpeech FastSpeech2 model (espnet/kan-bayashi_ljspeech_fastspeech2) from HuggingFace Hub. In the submitted system, the pre-trained model is the active model, as no custom training has been completed. Both the model and the vocoder run on CPU (device="cpu").
```

**Replace with:**

```
FastSpeech2Service first checks whether a 10-best averaged checkpoint exists at
training/exp/tts_fastspeech2_gst/valid.loss.ave_10best.pth, as this produces higher
quality output than a single checkpoint. If that file is not found, it falls back to
the single best checkpoint at training/exp/tts_fastspeech2_gst/valid.loss.best.pth.
If neither file is present, the service automatically downloads and loads the
pre-trained ESPnet LJSpeech FastSpeech2 model (espnet/kan-bayashi_ljspeech_fastspeech2)
from HuggingFace Hub. In the submitted system, the pre-trained model is the active
model, as no custom training has been completed. Both the model and the vocoder run
on CPU (device="cpu").
```

---

### 3. Section 3.6.3 — Rate limiting key

**Find:**

```
a rate limiter is applied to the TTS endpoint (20 requests per minute per user)
```

**Replace with:**

```
a rate limiter is applied to the TTS endpoint (20 requests per minute per IP address)
```

---

### 4. Section 3.6.3 — Environment variables table — add MAIL_PORT and APPLE_CLIENT_ID

**Find the environment variable block:**

```
DATABASE_URL       = postgresql://username:password@host:port/database_name
JWT_SECRET_KEY     = <a strong random secret used to sign JSON Web Tokens>
MAIL_USERNAME      = <SMTP email address for sending verification emails>
MAIL_PASSWORD      = <SMTP password>
MAIL_FROM          = <sender address>
MAIL_SERVER        = <SMTP server hostname>
GOOGLE_CLIENT_ID   = <Google OAuth2 client ID, if OAuth login is used>
MICROSOFT_CLIENT_ID= <Microsoft OAuth2 client ID, if OAuth login is used>
```

**Replace with:**

```
DATABASE_URL       = postgresql://username:password@host:port/database_name
JWT_SECRET_KEY     = <a strong random secret used to sign JSON Web Tokens>
MAIL_USERNAME      = <SMTP email address for sending verification emails>
MAIL_PASSWORD      = <SMTP password>
MAIL_FROM          = <sender address>
MAIL_PORT          = <SMTP port number, e.g. 587 for TLS or 465 for SSL>
MAIL_SERVER        = <SMTP server hostname>
GOOGLE_CLIENT_ID   = <Google OAuth2 client ID, if Google login is used>
MICROSOFT_CLIENT_ID= <Microsoft OAuth2 client ID, if Microsoft login is used>
APPLE_CLIENT_ID    = <Apple OAuth2 client ID, if Apple Sign-In is used>
```

---

### 5. Section 3.4.4 — Audio output format

**Find:**

```
This array is written to disk as a 16-bit PCM WAV file using the soundfile library.
```

**Replace with:**

```
This array is written to disk as a 32-bit float WAV file using the soundfile library.
```

---

### 6. Section 3.7.2 — Prosody Mapping pseudocode (full replacement)

**Find the entire pseudocode block:**

```
BEGIN Prosody_Mapping
pitch_scalar ← 1.0; energy_scalar ← 1.0; duration_scalar ← 1.0
IF emotion == 'Happy' THEN
pitch_scalar ← 1.15; energy_scalar ← 1.10; duration_scalar ← 0.90
ELSE IF emotion == 'Sad' THEN
pitch_scalar ← 0.85; energy_scalar ← 0.75; duration_scalar ← 1.25
ELSE IF emotion == 'Angry' THEN
pitch_scalar ← 1.25; energy_scalar ← 1.40; duration_scalar ← 0.85
END IF
adjusted_pitch   ← base_variance_vectors.pitch    * pitch_scalar
adjusted_energy  ← base_variance_vectors.energy   * energy_scalar
adjusted_duration← base_variance_vectors.duration * duration_scalar
RETURN (adjusted_pitch, adjusted_energy, adjusted_duration)
END Prosody_Mapping
```

**Replace with:**

```
BEGIN Prosody_Mapping
  // Default: neutral baseline
  pitch_shift  ← 0.00
  energy_shift ← 0.00
  speed        ← 1.00

  IF emotion == 'Angry'    THEN pitch_shift ←  0.20; energy_shift ←  0.35; speed ← 1.20
  IF emotion == 'Fear'     THEN pitch_shift ←  0.10; energy_shift ← -0.10; speed ← 1.10
  IF emotion == 'Happy'    THEN pitch_shift ←  0.15; energy_shift ←  0.20; speed ← 1.15
  IF emotion == 'Neutral'  THEN pitch_shift ←  0.00; energy_shift ←  0.00; speed ← 1.00
  IF emotion == 'Sad'      THEN pitch_shift ← -0.10; energy_shift <- -0.30; speed ← 0.70
  IF emotion == 'Surprise' THEN pitch_shift ←  0.25; energy_shift ←  0.15; speed ← 1.05

  // Pitch and energy are applied as additive offsets to the
  // FastSpeech2 variance predictor outputs.
  // Speed is converted to a duration-stretch factor alpha,
  // where alpha < 1.0 shortens phoneme durations (faster speech)
  // and alpha > 1.0 lengthens them (slower speech).
  adjusted_pitch  ← base_pitch  + pitch_shift
  adjusted_energy ← base_energy + energy_shift
  alpha           ← 1.0 / speed

  RETURN (adjusted_pitch, adjusted_energy, alpha)
END Prosody_Mapping
```

---

### 7. Table 3.5 — Add Fear and Surprise rows

In Table 3.5 (Prosody Parameter Values by Emotion), update all rows to match the values below. Replace the entire table content with:

| Emotion  | Pitch Shift | Energy Shift | Speed | Alpha (= 1/Speed) |
| -------- | ----------- | ------------ | ----- | ----------------- |
| Angry    | +0.20       | +0.35        | 1.20  | 0.83              |
| Fear     | +0.10       | −0.10        | 1.10  | 0.91              |
| Happy    | +0.15       | +0.20        | 1.15  | 0.87              |
| Neutral  | 0.00        | 0.00         | 1.00  | 1.00              |
| Sad      | −0.10       | −0.30        | 0.70  | 1.43              |
| Surprise | +0.25       | +0.15        | 1.05  | 0.95              |

_Pitch shift and energy shift are additive offsets applied to the FastSpeech2 variance predictor outputs. Alpha is the duration-stretch parameter passed to the ESPnet2 decode_conf._

---

### 8. Section 3.7.1 — Add EMOTION_MAP explanation

**Find the sentence:**

```
Both the label and its associated probability are returned.
```

**Replace with:**

```
Both the label and its associated probability are returned. Note that the underlying
j-hartmann/emotion-english-distilroberta-base model produces seven raw output labels
(angry, disgust, fear, happy, neutral, sad, surprise). The disgust label is remapped
to neutral by an internal EMOTION_MAP lookup table before being returned to the calling
function, yielding exactly six application-level emotion categories.
```

---

### 9. Section 3.8.1 — Confidence score — fix "seven emotion classes"

**Find:**

```
After the DistilRoBERTa model produces raw output values (logits) for each of the seven emotion classes, a softmax function converts these into probabilities that sum to one.
```

**Replace with:**

```
After the DistilRoBERTa model produces raw output values (logits) for each of its
seven raw output classes, a softmax function converts these into probabilities that
sum to one. The disgust class is remapped to neutral prior to synthesis, so the
system exposes six application-level emotion labels.
```

---

### 10. Section 4.2.3 — Computational Requirements — fix CPU/GPU contradiction

**Find:**

```
Sustaining an average response time of 600 milliseconds requires GPU-accelerated inference. Testing conducted on CPU-only hardware extended this latency to approximately five to eight seconds per request, which is impractical for real-time use.
```

**Replace with:**

```
Benchmarking conducted on GPU-equipped hardware demonstrated an average end-to-end
response time of 600 milliseconds. The submitted system, however, is configured to
run entirely on CPU (device="cpu" is set in both the FastSpeech2 and HiFi-GAN service
initialisers). On CPU-only hardware, latency extends to approximately five to eight
seconds per request, which is impractical for real-time use. Enabling GPU acceleration
in a production deployment is therefore recommended to reach the 600-millisecond target.
```

---

### 11. Section 5.4 Recommendations — Docker already implemented

**Find:**

```
Transitioning from local server deployment to cloud infrastructure would make the system capable of serving a large number of concurrent users. This would involve containerising the application using Docker and deploying it on scalable cloud platforms, with load balancing configured to distribute inference requests across multiple server instances.
```

**Replace with:**

```
The application has already been containerised using Docker; a production-ready
Dockerfile is included in the backend root of the repository. The next step is to
deploy this image to a scalable cloud infrastructure capable of serving a large
number of concurrent users. This would involve hosting the container on a managed
cloud platform such as AWS ECS, Google Cloud Run, or Azure Container Apps, with a
load balancer configured to distribute inference requests across multiple server
instances as demand grows.
```

---

### 12. Abstract — emotion category count

**Find:**

```
a fine-tuned DistilRoBERTa transformer for emotion classification into happy, sad, and neutral categories
```

**Replace with:**

```
a fine-tuned DistilRoBERTa transformer for emotion classification into six categories: angry, fear, happy, neutral, sad, and surprise
```

---

### 13. Section 1.3 Objectives — emotion category count

**Find:**

```
classify the emotional content of input text into distinct categories (happy, sad, neutral)
```

**Replace with:**

```
classify the emotional content of input text into six distinct categories (angry, fear, happy, neutral, sad, and surprise)
```

---

### 14. Section 3.8.4 — Intelligibility collection method clarification

**Find:**

```
This metric is collected alongside MOS via the same in-application feedback mechanism. The acceptable minimum threshold is 95%.
```

**Replace with:**

```
In this study, intelligibility is collected alongside MOS via the same in-application
feedback mechanism. Because obtaining exact word-identification counts from end users
is impractical, the interface uses a 1–5 rating scale (1 = very difficult to understand,
5 = perfectly clear) as a subjective proxy. The formula above defines the theoretical
basis for the metric; the database stores the collected 1–5 rating. The acceptable
minimum rating is 4 out of 5, corresponding approximately to the 95% threshold.
```

---

## STRUCTURAL FIXES (renumbering — no text to paste, just actions in Word)

---

### 15. Duplicate section 3.7 heading

In the Navigation Pane, find the second heading labelled **3.7** (the one titled _System Algorithm_).
Change its number and title to: **3.8 System Algorithm**

Then find the heading currently labelled **3.8** (_Evaluation Metrics and Measurement Criteria_).
Change it to: **3.9 Evaluation Metrics and Measurement Criteria**

Update all cross-references to 3.8 and 3.9 accordingly throughout Chapters 3, 4, and 5.

---

### 16. Missing subsection 3.7.2

Between the paragraph ending with _"All deep learning inference is performed on the CPU…"_ and the heading **3.7.3 Class Diagram**, insert a new Heading 3:

```
3.7.2   Development Environment and Technology Stack
```

Then move Tables 3.2, 3.3, and 3.4 (and their surrounding text) under this new heading.

---

### 17. Figure 3.4 missing — renumber Figure 3.5

Find the caption currently reading:

```
Figure 3.5: System Flowchart
```

Change it to:

```
Figure 3.4: System Flowchart
```

Update the List of Figures entry and every in-text reference from _Figure 3.5_ to _Figure 3.4_.

---

### 18. Table numbering conflict in Chapter 4

Rename the tables in Chapter 4 body and in the List of Tables as follows:

| Old label                                               | New label     | Title                                                                       |
| ------------------------------------------------------- | ------------- | --------------------------------------------------------------------------- |
| Table 4.1 (Inference Output Samples / Confusion Matrix) | **Table 4.1** | Confusion Matrix for Emotion Classification (Predicted vs. Actual, n = 120) |
| Table 4.2 (Per-Class Precision/Recall)                  | **Table 4.2** | Per-Class Precision, Recall, and Overall Accuracy                           |
| Table 4.2 (Latency — duplicate)                         | **Table 4.3** | Average Component Latency Across the Processing Pipeline                    |
| Table 4.3 (Audio Quality)                               | **Table 4.4** | Quantitative Audio Quality Evaluation Metrics                               |

Update the List of Tables and every in-text reference (e.g. _"Table 4.2 shows…"_) to use the new numbers.
