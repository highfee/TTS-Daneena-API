# Start from a robust Python image with Debian so we can install system packages
FROM python:3.10-slim

# Set huggingface space required user
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Working directory
WORKDIR $HOME/app

# Install system dependencies required for ML & Audio Processing
# Using root privileges briefly to install
USER root
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    sox \
    libpq-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*
USER user

# Copy requirements.txt, ensure correct permissions
COPY --chown=user:user requirements.txt .

# Install dependencies (no-cache to save disk space)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Auto-accept Coqui TTS license agreement
ENV COQUI_TOS_AGREED=1


# Download NLTK data at build time so it's available at runtime
# RUN python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng')"
RUN python -c "from TTS.api import TTS; TTS('tts_models/multilingual/multi-dataset/xtts_v2')"

# Copy the rest of the backend files
COPY --chown=user:user . .

# Hugging Face Spaces expects the app to run on port 7860
EXPOSE 7860

# Start the FastAPI application with proxy headers enabled
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*"]
