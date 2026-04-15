# EA-TTS System Diagrams (Mermaid.js)

All diagrams are based directly on the implemented source code.

---

## Figure 3.1 — System Architecture Workflow

```mermaid
flowchart TD
    subgraph CL["Client Layer"]
        UI["Next.js Frontend\n(TypeScript / React)"]
    end

    subgraph AL["API Layer"]
        FA["FastAPI + Uvicorn\nJWT Auth · Rate Limiter\n(20 req/min per IP)"]
    end

    subgraph IL["Intelligence Layer"]
        EC["EmotionClassifier\nDistilRoBERTa\n(j-hartmann/emotion-english-distilroberta-base)"]
        PC["ProsodyController\nEmotion → pitch_shift\nenergy_shift · speed"]
    end

    subgraph SL["Synthesis Layer"]
        FS["FastSpeech2Service\nESPnet2 Text2Speech\n(LJSpeech / GST fine-tune)"]
        HG["HiFiGANService\nGAN Vocoder\n22 050 Hz WAV"]
    end

    subgraph PL["Persistence Layer"]
        DB[("PostgreSQL\nSQLAlchemy ORM")]
        FS2["Local File Storage\napp/media/tts/{id}.wav"]
    end

    UI -->|"POST /tts/generate"| FA
    FA --> EC
    EC -->|"emotion, confidence"| PC
    PC -->|"prosody dict"| FS
    FS -->|"mel-spectrogram"| HG
    HG -->|"audio waveform"| FS2
    FS2 -->|"audio_url"| FA
    FA -->|"200 OK + audio_url"| UI
    FA -.->|"BackgroundTask INSERT"| DB
```

---

## Figure 3.2 — Class Diagram

```mermaid
classDiagram
    class User {
        +UUID id
        +String email
        +String hashed_password
        +Boolean is_active
        +DateTime created_at
    }

    class Chat {
        +UUID id
        +UUID user_id
        +String title
        +DateTime created_at
        +DateTime updated_at
    }

    class TTSRequest {
        +UUID id
        +UUID user_id
        +UUID chat_id
        +Text input_text
        +String detected_emotion
        +Float confidence_score
        +Text audio_path
        +Integer latency_ms
        +DateTime created_at
    }

    class AudioQualityMetric {
        +UUID id
        +UUID tts_request_id
        +Integer mos_score
        +Integer intelligibility
        +DateTime created_at
    }

    class EmotionMetric {
        +UUID id
        +UUID tts_request_id
        +String predicted_emotion
        +String actual_emotion
        +Boolean is_correct
    }

    class AuthToken {
        +UUID id
        +UUID user_id
        +String token
        +DateTime expires_at
        +Boolean used
        +DateTime created_at
    }

    class RefreshToken {
        +UUID id
        +UUID user_id
        +String token
        +DateTime expires_at
        +Boolean revoked
        +DateTime created_at
    }

    class EmotionClassifier {
        +pipeline emotion_classifier
        +dict EMOTION_MAP
        +detect_emotion(text) tuple
    }

    class ProsodyController {
        +dict PROSODY_PRESETS
        +get_prosody(emotion) dict
    }

    class FastSpeech2Service {
        +Text2Speech tts
        +dict _refs
        +Boolean _has_gst
        +synthesize(text, prosody, emotion) Tensor
    }

    class HiFiGANService {
        +String _mode
        +vocode(mel) ndarray
    }

    User "1" --> "0..*" Chat : owns
    User "1" --> "0..*" TTSRequest : submits
    User "1" --> "0..*" AuthToken : holds
    User "1" --> "0..*" RefreshToken : holds
    Chat "1" --> "0..*" TTSRequest : contains
    TTSRequest "1" --> "0..1" AudioQualityMetric : rated by
    TTSRequest "1" --> "0..1" EmotionMetric : evaluated by

    EmotionClassifier ..> TTSRequest : classifies emotion for
    ProsodyController ..> FastSpeech2Service : provides prosody to
    FastSpeech2Service ..> HiFiGANService : feeds mel-spectrogram to
```

---

## Figure 3.3 — Sequence Diagram

```mermaid
sequenceDiagram
    actor User
    participant FE as Next.js Frontend
    participant API as FastAPI Router
    participant Auth as JWT Middleware
    participant EC as EmotionClassifier
    participant PC as ProsodyController
    participant FS as FastSpeech2Service
    participant HG as HiFiGANService
    participant Store as File Storage
    participant DB as PostgreSQL

    User->>FE: Enter text, submit
    FE->>API: POST /tts/generate {text, chat_id}
    API->>Auth: Validate JWT (optional)
    Auth-->>API: user_id (or None)
    API->>API: Rate limit check (20/min per IP)

    API->>EC: detect_emotion(text)
    Note over EC: Check lru_cache(256)<br/>Run DistilRoBERTa if miss
    EC-->>API: (emotion, confidence)

    API->>PC: get_prosody(emotion)
    PC-->>API: {pitch_shift, speed, energy_shift}

    API->>FS: synthesize(text, prosody, emotion)
    Note over FS: Check lru_cache(64)<br/>Run ESPnet pipeline if miss<br/>alpha = 1 / speed
    FS-->>API: mel-spectrogram tensor

    API->>HG: vocode(mel)
    HG-->>API: audio waveform (float32)

    API->>API: Normalize audio (/ max_abs * 0.95)
    API->>Store: sf.write(app/media/tts/{uuid}.wav, audio, 22050)
    Store-->>API: file saved

    API-->>FE: 200 OK {id, emotion, confidence, audio_url, latency_ms}
    FE-->>User: Display emotion badge + audio player

    API-)DB: BackgroundTask: INSERT tts_requests\n(user_id, text, emotion, confidence, path, latency)
```

---

## Figure 3.4 — System Flowchart

```mermaid
flowchart TD
    A([Receive POST /tts/generate]) --> B{Validate JWT\n+ rate limit}
    B -->|"429 Too Many Requests"| ERR1([Return 429])
    B -->|OK| C{Check synthesis\ncache\nlru_cache 64}

    C -->|Hit| D[Retrieve cached\naudio array]
    C -->|Miss| E{Check emotion\ncache\nlru_cache 256}

    E -->|Hit| F[Return cached\nemotion + confidence]
    E -->|Miss| G[Run DistilRoBERTa\ninference\ntorch.no_grad]
    G --> H[Softmax logits\n→ argmax\n→ map EMOTION_MAP]
    H --> I[Cache emotion result\nlru_cache 256]
    I --> F

    F --> J[ProsodyController\nLookup PROSODY_PRESETS]
    D --> K
    J --> K[ESPnet pipeline\nNLTK POS tagging\nG2P → phoneme IDs]
    K --> L[FastSpeech2 encoder\n→ variance predictors]
    L --> M[Apply prosody:\nalpha = 1 / speed\npitch_shift · energy_shift]
    M --> N[FastSpeech2 decoder\n→ mel-spectrogram T×80]
    N --> O[HiFi-GAN vocoder\n→ float32 waveform]
    O --> P[Normalise:\naudio / max_abs × 0.95]
    P --> Q[Cache audio result\nlru_cache 64]

    Q --> R[sf.write\napp/media/tts/{uuid}.wav\n22 050 Hz]
    R --> S[Return HTTP 200\naudio_url · emotion\nconfidence · latency_ms]
    S --> T([BackgroundTask:\nINSERT to PostgreSQL])
```

---

## Algorithm 3.8.1 — Emotion Detection

```mermaid
flowchart TD
    A([BEGIN Emotion_Detection\nInput: text: str]) --> B{lru_cache hit?\nmaxsize=256}
    B -->|Yes| G
    B -->|No| C[RobertaTokenizerFast\nBPE tokenise + attention mask\nPad/truncate to 512 tokens]
    C --> D["DistilRoBERTa\nSequenceClassification\n(torch.no_grad)"]
    D --> E["Softmax(logits, dim=1)\n→ probability vector\n7 classes"]
    E --> F["ArgMax → max_idx\nconfidence = probs[max_idx]"]
    F --> F2["EMOTION_MAP lookup:\ndisgust → neutral\nothers pass through"]
    F2 --> G["Cache (emotion, confidence)"]
    G --> H([RETURN emotion: str\nconfidence: float])
```

---

## Algorithm 3.8.2 — Prosody Mapping

```mermaid
flowchart TD
    A([BEGIN Prosody_Mapping\nInput: emotion: str]) --> B{emotion}

    B -->|angry| C["pitch_shift = +0.20\nspeed = 1.20\nenergy_shift = +0.35"]
    B -->|fear| D["pitch_shift = +0.10\nspeed = 1.10\nenergy_shift = −0.10"]
    B -->|happy| E["pitch_shift = +0.15\nspeed = 1.15\nenergy_shift = +0.20"]
    B -->|neutral| F["pitch_shift = 0.00\nspeed = 1.00\nenergy_shift = 0.00"]
    B -->|sad| G["pitch_shift = −0.10\nspeed = 0.70\nenergy_shift = −0.30"]
    B -->|surprise| H["pitch_shift = +0.25\nspeed = 1.05\nenergy_shift = +0.15"]
    B -->|unknown| F

    C & D & E & F & G & H --> I([RETURN dict\npitch_shift · speed · energy_shift])
```

---

## Algorithm 3.8.3 — TTS Generation Pipeline

```mermaid
flowchart TD
    A([BEGIN TTS_Pipeline\nInput: text, emotion,\npitch_shift, energy_shift, speed]) --> B{lru_cache hit?\nmaxsize=64\nkey=text+emotion+prosody}

    B -->|Hit| J
    B -->|Miss| C[ESPnet preprocessing:\nNLTK POS tagging\nG2P → phoneme sequence\nToken ID encoding\n→ tensor shape 1×T_phoneme]

    C --> D{Local GST model\nor pretrained fallback?}

    D -->|Pretrained LJSpeech\nfallback| E["Text2Speech.from_pretrained\n(espnet/kan-bayashi_ljspeech_fastspeech2)\ndecode_conf alpha = 1/speed\nBuilt-in vocoder → wav"]
    E --> J

    D -->|Local GST model| F["Text2Speech from\ntraining/exp/tts_fastspeech2_gst/\nRef audio injected to GST encoder\ndecode_conf alpha = 1/speed\n→ feat_gen_denorm mel T×80"]
    F --> G[HiFiGANService.vocode\nfine-tuned generator or\nESPnet pretrained vocoder\n→ float32 waveform]
    G --> J

    J[Normalise:\nmax_abs = max of abs audio\naudio = audio / max_abs × 0.95] --> K[Cache audio array\nlru_cache 64]
    K --> L([RETURN audio: ndarray\nfloat32 · 22 050 Hz])
```

---

## Algorithm 3.8.4 — Database Logging

```mermaid
flowchart TD
    A([BEGIN Database_Transaction\nInput: request_id, user_id, text,\nemotion, confidence, file_path,\nlatency, chat_id]) --> B[Validate chat_id\nas UUID or None]

    B --> C["Create TTSRequest ORM object:\nid = request_id\nuser_id · input_text\ndetected_emotion · confidence_score\naudio_path · latency_ms · chat_id"]

    C --> D[db.add tts_request]
    D --> E{db.commit}

    E -->|Success| F[db.refresh tts_request]
    F --> G([RETURN — response\nalready sent to client])

    E -->|Exception| H[db.rollback]
    H --> I[log_error]
    I --> G
```

---

## Bonus — Auth Flow Sequence

```mermaid
sequenceDiagram
    actor User
    participant FE as Next.js Frontend
    participant API as FastAPI /auth
    participant DB as PostgreSQL
    participant Email as SMTP Server

    Note over User,Email: Email-code login
    User->>FE: Enter email address
    FE->>API: POST /auth/start {email}
    API->>DB: Find or create User by email
    API->>API: Generate 6-char auth token\n(expires 10 min)
    API->>DB: INSERT AuthToken
    API->>Email: Send auth code email
    API-->>FE: {message: "code sent"}

    User->>FE: Enter auth code
    FE->>API: POST /auth/verify {email, token}
    API->>DB: Lookup AuthToken\nvalidate not used / not expired
    API->>DB: Mark token used=True
    API->>API: create_access_token (JWT)\ngenerate_refresh_token
    API->>DB: INSERT RefreshToken (7 days)
    API-->>FE: {access_token, user_id, email}\n+ Set-Cookie: refresh_token (httpOnly)

    Note over User,Email: Token refresh (rotation)
    FE->>API: POST /auth/refresh\n(Cookie: refresh_token)
    API->>DB: Validate RefreshToken\nnot revoked / not expired
    API->>DB: Revoke old token
    API->>API: Issue new access_token\n+ new refresh_token
    API->>DB: INSERT new RefreshToken
    API-->>FE: {access_token}\n+ Set-Cookie: new refresh_token
```
