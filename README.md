---
title: Daneena TTS Backend
emoji: 🎤
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

This will include:

- What must be installed
- Why it must be installed
- What can go wrong
- How to verify each step works
- What “success” looks like

---

# EA-TTS Backend

# Complete Setup Guide (From a Brand-New Windows PC)

This section explains **exactly what to install, why it is needed, and how to verify everything works**.

We assume:

- Fresh Windows PC
- No Python installed
- No PostgreSQL installed
- No project cloned yet

---

# 1. System Requirements

Minimum requirements:

- Windows 10 or 11 (64-bit)
- 8GB RAM minimum (16GB recommended)
- At least 10GB free disk space
- Internet connection (for downloading models)

⚠ Important:
First time running FastSpeech2 + HiFiGAN may download large model files (hundreds of MB).

---

# 2. Install Required Software

These are mandatory before touching the project.

---

## Step 1 — Install Python 3.10.0 **(we have done this already)**

Why?
The project is built and tested with Python 3.10. Some libraries (ESPnet, Torch) may break with newer versions.

1. Go to:
   [https://www.python.org/downloads/release/python-3100/](https://www.python.org/downloads/release/python-3100/)

2. Download:
   **Windows installer (64-bit)**

3. Run installer:
   ✔ CHECK: “Add Python to PATH”
   ✔ Click Install

After installation:

Open Command Prompt and type:

```
python --version
```

Expected output:

```
Python 3.10.0
```

If not:
Restart your computer.

---

## Step 2 — Install Git **(we have done this already)**

Why?
To clone the repository from version control.

1. Go to:
   [https://git-scm.com/download/win](https://git-scm.com/download/win)

2. Install with default settings.

Verify:

```
git --version
```

---

## Step 3 — Install PostgreSQL **(we have done this already)**

Why?
The backend stores users, requests, and metrics in a relational database.

1. Go to:
   [https://www.postgresql.org/download/windows/](https://www.postgresql.org/download/windows/)

2. Download Windows installer (64-bit)

3. During installation:

- Leave port as 5432
- Set a strong password for postgres user
- Remember this password

---

### Create Database and User

After installation:

Open SQL Shell (psql).

Run:

```sql
CREATE USER ea_tts_user WITH PASSWORD 'yourpassword';
CREATE DATABASE ea_tts OWNER ea_tts_user;
GRANT ALL PRIVILEGES ON DATABASE ea_tts TO ea_tts_user;
```

If this fails:
Check that PostgreSQL service is running.

---

# 3. Clone the Project **(we have done this already)**

Choose a folder where you want the project.

Example:

```
C:\Projects
```

Open Command Prompt:

```
cd C:\Projects
git clone <REPOSITORY_URL> backend
cd backend
```

Now you are inside the backend folder.

---

# 4. Create Virtual Environment

Why?
To isolate project dependencies from global Python.

Inside backend folder:

```
python -m venv venv
```

This creates a `venv` folder.

---

## Activate Virtual Environment

If using Command Prompt:

```
venv\Scripts\activate
```

If using Git bash **(which you are)**:

```
source venv\Scripts\activate
```

If using PowerShell:

```
.\venv\Scripts\Activate.ps1
```

You should see:

```
(venv) C:\Projects\backend>
```

That means it worked.

---

# 5. Install Python Dependencies

Now install everything required.

```
pip install -r requirements.txt
```

This may take time (Torch + ESPnet are large).

If errors occur:

- Make sure Python version is 3.10
- Make sure venv is activated

---

# 6. Create .env Configuration File

Inside backend folder:

Create a file named:

```
.env
```

Add:

```
DATABASE_URL=postgresql://ea_tts_user:yourpassword@localhost:5432/ea_tts
JWT_SECRET_KEY=THIS_SHOULD_BE_A_LONG_RANDOM_STRING

MAIL_USERNAME=your_email@example.com
MAIL_PASSWORD=your_email_app_password
MAIL_FROM=your_email@example.com
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com

GOOGLE_CLIENT_ID=
MICROSOFT_CLIENT_ID=
APPLE_CLIENT_ID=
```

Important:

- JWT_SECRET_KEY must be long and random.
- Never push real passwords to GitHub.

---

# 7. Run Database Migrations

This creates tables automatically.

Run:

```
alembic upgrade head
```

If successful:
You will see “Running upgrade…”

To confirm tables exist:
Open pgAdmin → check ea_tts database → Tables.

You should see:

- user
- tts_request
- audio_quality_metric
- chat
- refresh_token
- etc.

---

# 8. Start the Backend Server

With venv activated:

```
uvicorn app.main:app --reload
```

Expected output:

```
Uvicorn running on http://127.0.0.1:8000
```

---

# 9. Verify Everything Works

Open browser:

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

You should see Swagger API documentation.

Test endpoint:

- Expand `/tts/generate`
- Click “Try it out”
- Enter text
- Click Execute

If successful:
You get emotion + audio URL.

---

# 10. First-Time AI Model Download

Important:

First time generating speech:

- Transformers downloads emotion model.
- ESPnet loads FastSpeech2.
- HiFiGAN loads vocoder.

This may take time.
Be patient.

After first run:
It becomes faster.

---

# 11. Where Audio Files Are Stored

Inside backend folder:

Look for:

```
media/
```

Generated `.wav` files are stored there.

---

# 12. Common Errors and Fixes

## Error: “Module not found”

Solution:
Make sure venv is activated.

---

## Error: “Database connection refused”

Solution:

- Check PostgreSQL service is running.
- Check DATABASE_URL in .env.

---

## Error: “Torch CUDA error”

If you don’t have GPU:
Use CPU version.
That is fine for demo.

---

## Error: Port 8000 already in use

Run:

```
uvicorn app.main:app --reload --port 8001
```

---

# 13. How To Know Everything Is Working Correctly

Checklist:

✔ Python 3.10 installed
✔ Git installed
✔ PostgreSQL installed
✔ Database created
✔ venv created and activated
✔ Dependencies installed
✔ .env file configured
✔ Alembic migration successful
✔ Uvicorn running
✔ Swagger docs accessible
✔ Audio file generated

If all are true:
System is fully operational.

---

# FURTHER READINGS

---

---

# EA-TTS Backend

# Complete Architecture, Setup & Technical Guide

---

# 1. What This Project Is (In Plain Language)

This project is an **Emotion-Adaptive Text-to-Speech (EA-TTS) System**.

It is a backend web application that:

1. Receives text from a user.
2. Uses Artificial Intelligence to detect the emotion in that text.
3. Modifies speech characteristics (pitch, speed, energy) based on that emotion.
4. Generates synthetic speech that reflects the emotional tone.
5. Stores the request and performance metrics in a database.
6. Returns the generated audio to the frontend.

Unlike normal text-to-speech systems that sound robotic and flat, this system tries to sound:

- Happy
- Sad
- Neutral

It is not just a demo script.
It is a structured AI backend system with authentication, database logging, performance tracking, and modular architecture.

---

# 2. High-Level Architecture (Big Picture)

When a user types text into the web app:

User → Frontend → FastAPI Backend → Emotion Model → Prosody Mapping → FastSpeech2 → HiFiGAN → Audio File → Database → Response Returned

Let’s explain that clearly.

---

# 3. Core Technical Concepts (Explained Simply)

Before understanding the code, these terms must be clear.

---

## 3.1 What Is a Backend?

A backend is the part of an application that:

- Runs on a server
- Handles business logic
- Processes data
- Communicates with databases
- Sends responses back to users

The frontend (like a React app) sends requests to the backend.

---

## 3.2 What Is an API?

API = Application Programming Interface.

It is a communication bridge between systems.

In this project:

Frontend sends HTTP request → Backend processes it → Backend returns JSON response.

Example:

POST `/tts/generate`

Request:

```json
{
  "text": "I am excited today"
}
```

Response:

```json
{
  "emotion": "happy",
  "confidence": 0.91,
  "audio_url": "/tts/audio/123"
}
```

---

## 3.3 What Is a REST API?

REST = Representational State Transfer.

A REST API:

- Uses HTTP methods (GET, POST, PUT, DELETE)
- Uses URLs to represent resources
- Returns structured data (usually JSON)

Examples in this project:

- GET `/tts/audio/{id}` → retrieve audio
- POST `/tts/generate` → create TTS request
- POST `/auth/start` → start authentication

---

## 3.4 What Is ASGI?

ASGI = Asynchronous Server Gateway Interface.

It allows Python web applications to handle multiple requests at the same time efficiently.

FastAPI is built on ASGI.

This allows:

- Non-blocking operations
- Better performance
- Scalability

---

## 3.5 What Is Uvicorn?

Uvicorn is an ASGI server.

It runs the FastAPI app.

Command:

```
uvicorn app.main:app --reload
```

Without Uvicorn, the backend cannot run.

---

## 3.6 What Is an ORM?

ORM = Object Relational Mapper.

It allows you to interact with a database using Python classes instead of raw SQL.

Instead of writing:

```sql
SELECT * FROM tts_request;
```

You write:

```python
db.query(TTSRequest).all()
```

This project uses SQLAlchemy as the ORM.

---

## 3.7 What Is SQLAlchemy?

SQLAlchemy:

- Connects Python to PostgreSQL
- Maps Python classes to database tables
- Manages database sessions

Each model in `app/models` becomes a table.

---

## 3.8 What Is PostgreSQL?

PostgreSQL is a relational database.

It stores:

- Users
- TTS requests
- Audio metrics
- Authentication tokens
- Feedback ratings

---

## 3.9 What Is Alembic?

Alembic handles database migrations.

Migration = version control for database schema.

If you modify a table, Alembic updates the database safely.

Command:

```
alembic upgrade head
```

---

## 3.10 What Is JWT?

JWT = JSON Web Token.

Used for authentication.

When a user logs in:

- Backend generates a signed token.
- Token is used to verify identity on future requests.

This allows secure stateless authentication.

---

## 3.11 What Is a Mel Spectrogram?

A mel spectrogram is:

A visual representation of sound frequencies over time.

Speech synthesis models generate this first.

It is not playable audio.

---

## 3.12 What Is a Vocoder?

A vocoder converts:

Mel spectrogram → real audio waveform.

In this project:
HiFiGAN is the vocoder.

---

## 3.13 What Is FastSpeech2?

FastSpeech2 is a deep learning TTS model.

It:

- Predicts pitch
- Predicts duration
- Predicts energy
- Generates mel spectrogram

It is fast and non-autoregressive.

---

## 3.14 What Is HuggingFace Transformers?

A Python library that provides pretrained NLP models.

Used here for emotion detection.

Model used:
`j-hartmann/emotion-english-distilroberta-base`

---

# 4. Detailed System Flow

Let’s follow one request.

---

## Step 1 – Request Received

User sends:

POST `/tts/generate`

FastAPI validates request using Pydantic schema.

---

## Step 2 – Emotion Detection

File: `emotion.py`

- Text is sent to Transformers pipeline.
- Model predicts emotion.
- Returns emotion + confidence score.

---

## Step 3 – Prosody Mapping

File: `prosody.py`

Maps emotion to speech adjustments.

Example:

Happy:

- Higher pitch
- Faster speed
- Higher energy

Sad:

- Lower pitch
- Slower speed
- Lower energy

---

## Step 4 – Speech Synthesis

File: `fastspeech.py`

- Converts text into tensor.
- Generates mel spectrogram.
- Applies pitch and energy shifts.

---

## Step 5 – Vocoding

File: `hifigan.py`

- Converts mel spectrogram into waveform.

---

## Step 6 – Audio Storage

`soundfile` writes `.wav` file to media folder.

---

## Step 7 – Database Logging

Creates `TTSRequest` record.

Stores:

- Text
- Emotion
- Confidence
- Latency
- Audio path

---

## Step 8 – Response Sent

Returns:

- Emotion
- Confidence
- Audio URL

Frontend plays audio.

---

# 5. Folder Structure Explained

## app/main.py

Creates FastAPI app.
Connects routers.
Initializes DB.
Creates media folder.

---

## app/core/

Configuration, security, email, rate limiting.

---

## app/models/

Database tables:

- user
- tts_request
- audio_quality_metric
- refresh_token
- chat

---

## app/schemas/

Defines API request/response structure using Pydantic.

---

## app/api/routes/

Defines API endpoints:

- auth
- tts
- chats

---

## app/services/

Business logic and AI:

- emotion detection
- prosody mapping
- FastSpeech2 wrapper
- HiFiGAN wrapper
- TTS pipeline

---

# 6. All Dependencies Explained

fastapi → API framework
uvicorn → runs server
sqlalchemy → ORM
psycopg2-binary → PostgreSQL driver
alembic → DB migration tool
pydantic → request validation
pydantic-settings → config loader
python-dotenv → loads `.env`
transformers → emotion detection
torch → deep learning engine
espnet → speech models
soundfile → save audio
fastapi-mail → email sending
python-jose → JWT handling
slowapi → rate limiting
requests → OAuth communication

---

# 7. Setup From Scratch (Step-by-Step)

1. Install Python 3.10
2. Install PostgreSQL
3. Create DB + user
4. Clone repository
5. Create virtual environment
6. Activate venv
7. Install dependencies
8. Create `.env` file
9. Run migrations
10. Start server

Then open:
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

# 8. What Makes This System Advanced

This backend demonstrates:

- AI integration (NLP + Speech synthesis)
- Layered architecture
- Authentication system
- Database schema design
- Performance tracking
- REST API design
- Modular services
- Production-style organization

It combines:

- Natural Language Processing
- Deep Learning
- Speech Synthesis
- Backend Engineering
- Database Management

---
